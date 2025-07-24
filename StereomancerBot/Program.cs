using F23.StringSimilarity;
using Imgur.API.Authentication;
using Imgur.API.Endpoints;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using SkiaSharp;
using System.Diagnostics;
using System.Text;

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

        private static StereomancerBot _bot;

        public class StereomancerBot
        {
            private HttpClient _client;
            const string customUserAgent = "windows:com.kra2008.stereomancerbot:v1 (by /u/kra2008)";

            public StereomancerBot()
            {
                _client = new HttpClient(); 
                _client.DefaultRequestHeaders.TryAddWithoutValidation("User-Agent", customUserAgent);
            }

            public async Task ConvertPosts(Creds creds, string sourceSubName, string destinationSubName)
            {
                try
                {
                    var imgurClient = new ApiClient(creds.ImgurClientId);
                    var convertedImageClient = new HttpClient();
                    var imageEndpoint = new ImageEndpoint(imgurClient, convertedImageClient);

                    var postsToConvert = await GetEligiblePosts(sourceSubName);
                    var existingPosts = await GetEligiblePosts(destinationSubName);
                    var alreadyConvertedByBot = await File.ReadAllTextAsync(crossPostedListPath);

                    Console.WriteLine("opted out users: " + string.Join(",", creds.OptedOutUsers));

                    var archivedPosts = postsToConvert.Where(post => post.archived);
                    var alreadyDonePosts = postsToConvert.Where(post => alreadyConvertedByBot.Contains(post.id));
                    var optedOutPosts = postsToConvert.Where(post => creds.OptedOutUsers.Contains(post.author));
                    var ownPosts = postsToConvert.Where(post => post.author == "StereomancerBot");

                    var jw = new JaroWinkler();
                    var doubledPosts = postsToConvert.Where(toConvert => existingPosts.Any(existing => jw.Similarity(toConvert.title, existing.title) > 0.90));

                    var invalidPosts = postsToConvert.Where(post => !post.url.ToString().EndsWith(".jpg") &&
                                                                    !post.url.ToString().EndsWith(".png") &&
                                                                    !post.url.ToString().EndsWith(".jpeg"));

                    var badPosts = postsToConvert.Where(post => post.upvote_ratio < 0.5);

                    var removeIds =
                        archivedPosts
                            .Concat(alreadyDonePosts)
                            .Concat(optedOutPosts)
                            .Concat(ownPosts)
                            .Concat(doubledPosts)
                            .Concat(invalidPosts)
                            .Concat(badPosts).Select(a => a.id);

                    postsToConvert = postsToConvert.Where(p => !removeIds.Contains(p.id)).ToList();

                    postsToConvert = postsToConvert.Take(MAX_POSTS_TO_MAKE).ToList();
                    Console.WriteLine("posting " + postsToConvert.Count() + " to " + destinationSubName);
                    foreach (var postToConvert in postsToConvert)
                    {
                        var originalImageClient = new HttpClient();
                        Stream originalImageStream;
                        try
                        {
                            var image = await originalImageClient.GetAsync(postToConvert.url);
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

                        Console.WriteLine("uploading image " + postToConvert.title);
                        var imageUpload = await imageEndpoint.UploadImageAsync(convertedImageStream, title: postToConvert.title,
                            description: "Originally posted to Reddit by " + postToConvert.author + ", converted by StereomancerBot");

                        var authToken = await GetAuthToken(creds);

                        Console.WriteLine("posting " + postToConvert.title);
                        var newPost =
                            await CreatePost(postToConvert.title + " (converted from r/" + sourceSubName + ")",
                                imageUpload.Link, destinationSubName, authToken, postToConvert.over_18);

                        Console.WriteLine("adding comment to new post");
                        await CreateComment(newPost.name, "Original post: " + postToConvert.permalink + " by [" + postToConvert.author + "](https://reddit.com/user/" + postToConvert.author + ")" +
                                                         "\r\n\r\n" +
                                                         "I'm a bot made by [KRA2008](https://reddit.com/user/KRA2008) to help the stereoscopic 3D community on Reddit :) " +
                                                         "I convert posts between cross and parallel viewing and repost them between the two subs. " +
                                                         "Please message [KRA2008](https://reddit.com/user/KRA2008) if you have comments or questions.", authToken);

                        Console.WriteLine("adding comment to existing post");
                        await CreateComment(postToConvert.name,"I'm a bot and I've converted this post to r/" + destinationSubName + " and you can see that here: " + newPost.permalink, authToken);

                        await File.AppendAllLinesAsync(crossPostedListPath, [postToConvert.id]);
                    }
                }
                catch (Exception e)
                {
                    Console.WriteLine(e);
                    Console.ReadLine();
                }
            }

            private async Task<string> GetAuthToken(Creds creds)
            {
                var authRequestContent = new MultipartFormDataContent();
                authRequestContent.Add(new StringContent("password"), "grant_type");
                authRequestContent.Add(new StringContent(creds.RedditUsername), "username");
                authRequestContent.Add(new StringContent(creds.RedditPassword), "password");
                authRequestContent.Add(new StringContent(creds.RedditRedirectUri), "redirect_uri");

                var authenticationString = creds.RedditClientId + ":" + creds.RedditClientSecret;
                var base64EncodedAuthenticationString = Convert.ToBase64String(Encoding.UTF8.GetBytes(authenticationString));
                Debug.WriteLine(base64EncodedAuthenticationString);
                _client.DefaultRequestHeaders.Remove("Authorization");
                _client.DefaultRequestHeaders.TryAddWithoutValidation("Authorization", "Basic " + base64EncodedAuthenticationString);

                var authResponse = await _client.PostAsync("https://www.reddit.com/api/v1/access_token", authRequestContent);
                authResponse.EnsureSuccessStatusCode();

                var responseContent = await authResponse.Content.ReadAsStringAsync();
                var resp = JsonConvert.DeserializeObject<AuthResponse>(responseContent);
                return resp.access_token;
            }

            private async Task<PostDetails> CreatePost(string title, string url, string subreddit, string authToken, bool isNsfw)
            {
                var postRequestContent = new MultipartFormDataContent();
                postRequestContent.Add(new StringContent(title), "title");
                postRequestContent.Add(new StringContent(url), "url");
                postRequestContent.Add(new StringContent(subreddit), "sr");
                postRequestContent.Add(new StringContent("link"), "kind");
                postRequestContent.Add(new StringContent(isNsfw.ToString()), "nsfw");

                _client.DefaultRequestHeaders.Remove("Authorization");
                _client.DefaultRequestHeaders.TryAddWithoutValidation("Authorization", "Bearer " + authToken);

                var postResponse = await _client.PostAsync("https://oauth.reddit.com/api/submit", postRequestContent);
                postResponse.EnsureSuccessStatusCode();

                var respString = await postResponse.Content.ReadAsStringAsync();
                var deserialized = JsonConvert.DeserializeObject<CreatedPostResponse>(respString);
                var jarray = deserialized.jquery
                    .FirstOrDefault(a => (long)a[0] == 10 &&
                                         (long)a[1] == 11 &&
                                         (string)a[2] == "call")?[3];
                var createdUrl = ((jarray as JArray).First() as JValue).ToString();

                _client.DefaultRequestHeaders.Remove("Authorization");
                var postDetailsResponse = await _client.GetAsync(createdUrl + ".json");
                postDetailsResponse.EnsureSuccessStatusCode();
                var postDetailsString = await postDetailsResponse.Content.ReadAsStringAsync();
                var postDetails = JsonConvert.DeserializeObject<PostDetails1[]>(postDetailsString);
                return postDetails.FirstOrDefault()?.data.children.FirstOrDefault()?.data;
            }

            private async Task CreateComment(string postName, string comment, string authToken)
            {
                var commentBody = new MultipartFormDataContent();
                commentBody.Add(new StringContent(postName), "thing_id");
                commentBody.Add(new StringContent(comment), "text");
                _client.DefaultRequestHeaders.Remove("Authorization");
                _client.DefaultRequestHeaders.TryAddWithoutValidation("Authorization", "Bearer " + authToken);
                var commentResponse = await _client.PostAsync("https://oauth.reddit.com/api/comment", commentBody);
                commentResponse.EnsureSuccessStatusCode();
            }

            private async Task<IEnumerable<ExistingPost>> GetEligiblePosts(string subredditName)
            {
                _client.DefaultRequestHeaders.Remove("Authorization");
                var allPostsResponse = await _client.GetAsync("https://www.reddit.com/r/" + subredditName + ".json");
                var existingPosts = new List<ExistingPost>();
                if (allPostsResponse.IsSuccessStatusCode)
                {
                    var responseString = await allPostsResponse.Content.ReadAsStringAsync();
                    var subreddit = JsonConvert.DeserializeObject<Subreddit>(responseString);
                    var posts = subreddit.data.children;
                    foreach (var post in posts)
                    {
                        if (post.data.is_gallery &&
                            !post.data.is_video)
                        {
                            Console.WriteLine("that's a gallery.");
                        }
                        else if (!post.data.is_video &&
                                 (post.data.url.EndsWith(".jpeg") ||
                                  post.data.url.EndsWith(".jpg") ||
                                  post.data.url.EndsWith(".png")))
                        {
                            existingPosts.Add(post.data);
                        }
                        else
                        {
                            Console.WriteLine("that's a video.");
                        }
                    }
                }

                return existingPosts;
            }
        }

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

            var bot = new StereomancerBot();
            DoCrossPosting(bot).Wait();

            Console.WriteLine("posting complete");
        }

        private static async Task DoCrossPosting(StereomancerBot bot)
        {
            if (!File.Exists(credsPath)) throw new Exception("No creds!");

            Creds? creds;
            using (var r = new StreamReader(credsPath))
            {
                var json = await r.ReadToEndAsync();
                creds = JsonConvert.DeserializeObject<Creds>(json);
            }
            if (creds == null) throw new Exception("Bad creds!");

            await bot.ConvertPosts(creds, "parallelview", "crossview");
            await bot.ConvertPosts(creds, "crossview", "parallelview");
        }
    }
}