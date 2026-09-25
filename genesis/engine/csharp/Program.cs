using System.Text.Json;
var health = new { component = "windows-bridge", status = "ok", runtime = Environment.Version.ToString() };
Console.WriteLine(JsonSerializer.Serialize(health));
