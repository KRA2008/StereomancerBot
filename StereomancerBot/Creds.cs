namespace StereomancerBot
{
    internal class Creds
    {
        public string RedditUsername { get; set; }
        public string RedditPassword { get; set; }
        public string RedditClientId { get; set; }
        public string RedditClientSecret { get; set; }
        public string RedditRedirectUri { get; set; }
        public string ImgurClientId { get; set; }
        public string ImgurClientSecret { get; set; }
        public string[] OptedOutUsers { get; set; }
    }
}
