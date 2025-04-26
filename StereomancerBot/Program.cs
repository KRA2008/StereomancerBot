using Imgur.API.Authentication;
using Imgur.API.Endpoints;
using Newtonsoft.Json;
using RedditSharp;
using RedditSharp.Things;
using SkiaSharp;
using F23.StringSimilarity;

namespace StereomancerBot
{
    public class Program
    {
        private static string appPath = Path.GetDirectoryName(System.Reflection.Assembly.GetExecutingAssembly().Location);
        private static string crossPostedListPath = Path.Combine(appPath, "CrossPosted.txt");
        private static string credsPath = Path.Combine(appPath, "creds.json");

        private const int MAX_POSTS_TO_MAKE = 10;
        private const int MAX_POSTS_TO_SEARCH = 100;
        private const int MAX_IMAGE_WIDTH = 2000;

        static void Main()
        {
            try
            {
                if (!File.Exists(crossPostedListPath))
                {
                    Console.WriteLine("cross posted list not found, creating");
                    File.Create(crossPostedListPath).Close();
                }
            }
            catch (Exception e)
            {
                Console.WriteLine("Error opening files: " + e); 
                Console.ReadLine();
            }

            DoCrossPosting().Wait();
            Console.WriteLine("posting complete");
        }

        private static async Task DoCrossPosting()
        {
            await ConvertPosts("parallelview", "crossview");
            await ConvertPosts("crossview", "parallelview");
        }

        private static async Task ConvertPosts(string sourceSubName, string destinationSubName)
        {
            try
            {
                if (!File.Exists(credsPath)) throw new Exception("No creds!");

                Creds? creds;
                using (var r = new StreamReader(credsPath))
                {
                    var json = await r.ReadToEndAsync();
                    creds = JsonConvert.DeserializeObject<Creds>(json);
                }
                if (creds == null) throw new Exception("Bad creds!");

                var redditAgent = new BotWebAgent(creds.RedditUsername, creds.RedditPassword, creds.RedditClientId, creds.RedditClientSecret, creds.RedditRedirectUri);
                var reddit = new Reddit(redditAgent, true);

                var imgurClient = new ApiClient(creds.ImgurClientId);
                var convertedImageClient = new HttpClient();
                var imageEndpoint = new ImageEndpoint(imgurClient, convertedImageClient);

                var sourceSubreddit = await reddit.GetSubredditAsync(sourceSubName);
                var destinationSubreddit = await reddit.GetSubredditAsync(destinationSubName);
                var postsToConvert = await sourceSubreddit.GetPosts(Subreddit.Sort.Hot, MAX_POSTS_TO_SEARCH).ToListAsync();
                var existingPosts = await destinationSubreddit.GetPosts(Subreddit.Sort.Hot, MAX_POSTS_TO_SEARCH).ToListAsync();
                var alreadyConvertedByBot = await File.ReadAllTextAsync(crossPostedListPath);

                Console.WriteLine("opted out users: " + string.Join(",",creds.OptedOutUsers));

                var archivedPosts = postsToConvert.Where(post => post.IsArchived);
                var oldPosts = postsToConvert
                    .Where(post => post.CreatedUTC < DateTime.UtcNow.Subtract(new TimeSpan(3, 0, 0, 0)));
                var alreadyDonePosts = postsToConvert.Where(post => alreadyConvertedByBot.Contains(post.Id));
                var optedOutPosts = postsToConvert.Where(post => creds.OptedOutUsers.Contains(post.AuthorName));
                var ownPosts = postsToConvert.Where(post => post.AuthorName == "StereomancerBot");

                var jw = new JaroWinkler();
                var doubledPosts = postsToConvert.Where(toConvert => existingPosts.Any(existing => jw.Similarity(toConvert.Title,existing.Title) > 0.90));

                var invalidPosts = postsToConvert.Where(post => !post.Url.ToString().EndsWith(".jpg") &&
                                                                !post.Url.ToString().EndsWith(".png") &&
                                                                !post.Url.ToString().EndsWith(".jpeg"));

                var badPosts = postsToConvert.Where(post => post.Score < 0 && post.Upvotes > 0);

                var removeIds =
                    archivedPosts
                        .Concat(oldPosts)
                        .Concat(alreadyDonePosts)
                        .Concat(optedOutPosts)
                        .Concat(ownPosts)
                        .Concat(doubledPosts)
                        .Concat(invalidPosts)
                        .Concat(badPosts).Select(a => a.Id);

                postsToConvert = postsToConvert.Where(p => !removeIds.Contains(p.Id)).ToList();

                postsToConvert = postsToConvert.Take(MAX_POSTS_TO_MAKE).ToList();
                Console.WriteLine("posting " + postsToConvert.Count + " to " + destinationSubName);
                foreach (var postToConvert in postsToConvert)
                {
                    var originalImageClient = new HttpClient();
                    Stream originalImageStream;
                    try
                    {
                        var image = await originalImageClient.GetAsync(postToConvert.Url);
                        image.EnsureSuccessStatusCode();
                        originalImageStream = await image.Content.ReadAsStreamAsync();
                    }
                    catch (Exception ex)
                    {
                        continue;
                    }

                    using var originalBitmap = SKBitmap.Decode(originalImageStream);
                    int newWidth, newHeight;
                    if (originalBitmap.Width > MAX_IMAGE_WIDTH)
                    {
                        newWidth = MAX_IMAGE_WIDTH;
                        var aspectRatio = originalBitmap.Height / (1f * originalBitmap.Width);
                        newHeight = (int)(aspectRatio * MAX_IMAGE_WIDTH);
                    }
                    else
                    {
                        newWidth = originalBitmap.Width;
                        newHeight = originalBitmap.Height;
                    }

                    var imageInfo = new SKImageInfo(newWidth, newHeight);
                    using var newSurface = SKSurface.Create(imageInfo);
                    newSurface.Canvas.DrawBitmap(originalBitmap,
                        new SKRect(0, 0, originalBitmap.Width, originalBitmap.Height),
                        new SKRect(imageInfo.Width / 2f, 0, imageInfo.Width * 3f / 2f, imageInfo.Height));
                    newSurface.Canvas.DrawBitmap(originalBitmap,
                        new SKRect(0, 0, originalBitmap.Width, originalBitmap.Height),
                        new SKRect(-imageInfo.Width / 2f, 0, imageInfo.Width / 2f, imageInfo.Height));

                    using var skImage = newSurface.Snapshot();
                    using var encoded = skImage.Encode(SKEncodedImageFormat.Jpeg, 100);
                    await using var convertedImageStream = encoded.AsStream();

                    Console.WriteLine("uploading image " + postToConvert.Title);
                    var imageUpload = await imageEndpoint.UploadImageAsync(convertedImageStream, title: postToConvert.Title,
                        description: "Originally posted to Reddit by " + postToConvert.AuthorName + ", converted by StereomancerBot");

                    Console.WriteLine("posting " + postToConvert.Title);
                    var crossPost = await destinationSubreddit.SubmitPostAsync(postToConvert.Title + " (converted from r/" + sourceSubName + ")", imageUpload.Link);

                    if (postToConvert.NSFW)
                    {
                        Console.WriteLine("marking NSFW");
                        await crossPost.MarkNSFWAsync();
                    }

                    Console.WriteLine("adding comment");
                    await crossPost.CommentAsync("Original post: https://reddit.com/r/" + sourceSubName + "/comments/" + postToConvert.Id + " by [" + postToConvert.AuthorName + "](https://reddit.com/user/" + postToConvert.AuthorName + ")" +
                                      "\r\n\r\n" +
                                      "I'm a bot made by [KRA2008](https://reddit.com/user/KRA2008) to help the stereoscopic 3D community on Reddit :) " +
                                      "I convert posts between cross and parallel viewing and repost them between the two subs. " +
                                      "Please message [KRA2008](https://reddit.com/user/KRA2008) if you have comments or questions.");

                    await postToConvert.CommentAsync("I'm a bot and I've converted this post to r/" + destinationSubName + " and you can see that here: https://reddit.com/r/" + destinationSubName + "/comments/" + crossPost.Id);

                    await File.AppendAllLinesAsync(crossPostedListPath, [postToConvert.Id]);
                }
            }
            catch (Exception e)
            {
                Console.WriteLine(e);
                Console.ReadLine();
            }
        }
    }
}