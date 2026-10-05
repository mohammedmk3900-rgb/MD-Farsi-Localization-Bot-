using System.Text.Json;

var result = new
{
    schema_version = 1,
    operation = "windows_probe",
    status = "ok",
    runtime = ".NET 10",
    generated_at = DateTimeOffset.UtcNow
};

Console.WriteLine(JsonSerializer.Serialize(result));
