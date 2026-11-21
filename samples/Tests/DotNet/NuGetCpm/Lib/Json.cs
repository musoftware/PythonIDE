namespace Lib;

public static class Json
{
    public static string Hello() => Newtonsoft.Json.JsonConvert.SerializeObject(new { Hello = "CPM" });
}
