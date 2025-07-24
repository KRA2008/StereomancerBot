namespace StereomancerBot;

public class PostDetails1
{
    public string kind { get; set; }
    public PostDetails2 data { get; set; }
}

public class PostDetails2
{
    public PostDetails3[] children { get; set; }
}

public class PostDetails3
{
    public string kind { get; set; }
    public PostDetails data { get; set; }
}

public class PostDetails
{
    public string name { get; set; }
    public string permalink { get; set; }
}