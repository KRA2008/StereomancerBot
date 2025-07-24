namespace StereomancerBot;

public class Subreddit
{
    public SubredditData data { get; set; }
}

public class SubredditData
{
    public IEnumerable<ExistingPostData> children { get; set; }
}

public class ExistingPostData
{
    public ExistingPost data { get; set; }
}

public class ExistingPost
{
    public string url { get; set; }
    public string author { get; set; }
    public string title { get; set; }
    public bool archived { get; set; }
    public string id { get; set; }
    public float upvote_ratio { get; set; }
    public bool is_video { get; set; }
    public bool is_gallery { get; set; }
    public bool over_18 { get; set; }
    public string name { get; set; }
    public string permalink { get; set; }
}