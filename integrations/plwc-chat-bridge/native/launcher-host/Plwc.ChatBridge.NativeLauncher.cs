using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Net.Sockets;
using System.Reflection;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Web.Script.Serialization;
using Microsoft.Win32;

internal static class Program
{
    private const string NativeHostName = "plwc.chat_bridge.launcher";
    private const string BuildIdentityResourceName = "Plwc.ChatBridge.BuildIdentity.json";
    private const string DevelopmentExtensionId = "nlogfcafjdfdoknpkbehjgihpafpipdb";
    private const string ChromeStoreExtensionId = "feceodobnhefdbfgmbinkndhogpfkicb";
    private const string EdgeStoreExtensionId = "nncomjknhhlgcmkmlaljhkiojcnpmflb";
    private const int ExpectedToolCount = 8;
    private const int MaxMessageBytes = 4096;
    private const int StartupTimeoutMilliseconds = 30000;

    private static readonly string AppDataRoot = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
        "PLwC");
    private static readonly string LogRoot = Path.Combine(AppDataRoot, "logs", "chat-bridge");
    private static readonly string StateRoot = Path.Combine(AppDataRoot, "state", "chat-bridge");
    private static readonly string LauncherLogPath = Path.Combine(LogRoot, "native-launcher.log");
    private static readonly string BridgeOutputLogPath = Path.Combine(LogRoot, "bridge.out.log");
    private static readonly string BridgeErrorLogPath = Path.Combine(LogRoot, "bridge.err.log");
    private static readonly string BridgePidPath = Path.Combine(StateRoot, "bridge.pid");

    private sealed class Layout
    {
        internal string BridgeEntry;
        internal string ConfigPath;
        internal string Endpoint;
        internal string HealthScript;
        internal string IntegrationRoot;
        internal string LaunchScript;
        internal int Port;
    }

    private sealed class BuildIdentity
    {
        public int schemaVersion { get; set; }
        public string product { get; set; }
        public string releaseVersion { get; set; }
        public string buildId { get; set; }
        public InstallerIdentity installer { get; set; }
        public ComponentVersions components { get; set; }
    }

    private sealed class InstallerIdentity
    {
        public string componentId { get; set; }
        public string directoryName { get; set; }
    }

    private sealed class ComponentVersions
    {
        public string nodeBridge { get; set; }
        public string browserExtension { get; set; }
        public string nativeLauncher { get; set; }
    }

    private static int Main(string[] args)
    {
        try
        {
            Directory.CreateDirectory(LogRoot);
            Directory.CreateDirectory(StateRoot);

            if (HasArgument(args, "--register"))
            {
                return RegisterNativeHost(args);
            }
            if (HasArgument(args, "--unregister"))
            {
                return UnregisterNativeHost(args);
            }
            if (HasArgument(args, "--status"))
            {
                return PrintRegistrationStatus(args);
            }
            if (HasArgument(args, "--build-identity"))
            {
                Console.WriteLine(SerializeBuildIdentity(LoadBuildIdentity()));
                return 0;
            }

            return RunNativeHost();
        }
        catch (Exception error)
        {
            AppendLog("fatal", error.ToString());
            if (HasCommandLineMode(args))
            {
                Console.Error.WriteLine(error.Message);
                return 1;
            }
            WriteResponse(false, "failed", "launcher_error", error.Message, 0);
            return 0;
        }
    }

    private static int RunNativeHost()
    {
        string request = ReadMessage();
        BuildIdentity buildIdentity = LoadBuildIdentity();
        bool german = Regex.IsMatch(request, "\"language\"\\s*:\\s*\"de(?:-|\\\")", RegexOptions.IgnoreCase);
        if (!Regex.IsMatch(request, "\"command\"\\s*:\\s*\"start\""))
        {
            WriteResponse(
                false,
                "failed",
                "unsupported_command",
                Text(german, "Der angeforderte Bridge-Befehl wird nicht unterstützt.", "The requested bridge command is not supported."),
                0);
            return 0;
        }
        string requestedBuildId = JsonStringValue(request, "buildId");
        if (!String.Equals(requestedBuildId, buildIdentity.buildId, StringComparison.Ordinal))
        {
            WriteResponse(
                false,
                "failed",
                "build_identity_mismatch",
                Text(
                    german,
                    "Die angeforderte Buildidentitaet stimmt nicht mit dem installierten Launcher ueberein.",
                    "The requested build identity does not match the installed launcher."),
                0);
            return 0;
        }

        bool ownsMutex = false;
        using (Mutex startupMutex = new Mutex(false, "Local\\PLwC.ChatBridge.Startup"))
        {
            try
            {
                try
                {
                    ownsMutex = startupMutex.WaitOne(TimeSpan.FromSeconds(40));
                }
                catch (AbandonedMutexException)
                {
                    ownsMutex = true;
                }
                if (!ownsMutex)
                {
                    WriteResponse(
                        false,
                        "failed",
                        "startup_busy",
                        Text(german, "Die Bridge-Einrichtung wird bereits ausgeführt.", "Bridge setup is already running."),
                        0);
                    return 0;
                }

                return StartAndVerifyBridge(german, buildIdentity);
            }
            finally
            {
                if (ownsMutex)
                {
                    startupMutex.ReleaseMutex();
                }
            }
        }
    }

    private static int StartAndVerifyBridge(bool german, BuildIdentity buildIdentity)
    {
        Layout layout;
        try
        {
            layout = ResolveLayout();
        }
        catch (FileNotFoundException error)
        {
            string code = error.Message.StartsWith("bridge_config_missing", StringComparison.Ordinal)
                ? "bridge_config_missing"
                : "bridge_files_missing";
            AppendLog(code, error.Message);
            WriteResponse(
                false,
                "failed",
                code,
                Text(
                    german,
                    "Die Bridge-Installation ist unvollständig. Starten Sie die PLwC-Einrichtung erneut.",
                    "The bridge installation is incomplete. Run PLwC Setup again."),
                0);
            return 0;
        }
        string nodePath = ResolveNodePath();
        if (nodePath == null)
        {
            WriteResponse(
                false,
                "failed",
                "node_missing",
                Text(
                    german,
                    "Node.js 22.12 oder neuer wurde nicht gefunden. Öffnen Sie die PLwC Bridge-Einrichtung.",
                    "Node.js 22.12 or newer was not found. Open PLwC Bridge Setup."),
                0);
            return 0;
        }

        string healthError;
        if (VerifyHealth(nodePath, layout, buildIdentity, out healthError))
        {
            AppendLog("ready", "Bridge already running with 8/8 tools.");
            WriteResponse(
                true,
                "already_running",
                "ready",
                Text(german, "Bridge ist verbunden, 8 von 8 Werkzeugen sind bereit.", "Bridge connected, 8 of 8 tools are ready."),
                ExpectedToolCount);
            return 0;
        }

        if (IsLoopbackPortOpen(layout.Port))
        {
            AppendLog("port_in_use", healthError);
            WriteResponse(
                false,
                "failed",
                "port_in_use",
                Text(
                    german,
                    "Port 3007 wird bereits verwendet, aber die PLwC Bridge ist dort nicht betriebsbereit. Prüfen Sie das Bridge-Protokoll.",
                    "Port 3007 is already in use, but PLwC Chat Bridge is not ready there. Check the bridge log."),
                0);
            return 0;
        }

        string launchOutput;
        string launchError;
        int launchExitCode = RunProcess(
            nodePath,
            QuoteArgument(layout.LaunchScript) +
                " --entry " + QuoteArgument(layout.BridgeEntry) +
                " --config " + QuoteArgument(layout.ConfigPath) +
                " --stdout " + QuoteArgument(BridgeOutputLogPath) +
                " --stderr " + QuoteArgument(BridgeErrorLogPath) +
                " --pid " + QuoteArgument(BridgePidPath),
            layout.IntegrationRoot,
            40000,
            out launchOutput,
            out launchError);
        AppendLog(
            "launch",
            "node=" + nodePath + "; exit=" + launchExitCode + "; output=" + launchOutput + "; error=" + launchError);
        if (launchExitCode != 0)
        {
            WriteResponse(
                false,
                "failed",
                "process_start_failed",
                Text(
                    german,
                    "Die PLwC Bridge konnte nicht gestartet werden. Prüfen Sie das Bridge-Protokoll.",
                    "PLwC Chat Bridge could not be started. Check the bridge log."),
                0);
            return 0;
        }

        Stopwatch timeout = Stopwatch.StartNew();
        while (timeout.ElapsedMilliseconds < StartupTimeoutMilliseconds)
        {
            Thread.Sleep(400);
            if (VerifyHealth(nodePath, layout, buildIdentity, out healthError))
            {
                AppendLog("ready", "Bridge started and verified with 8/8 tools.");
                WriteResponse(
                    true,
                    "started",
                    "ready",
                    Text(german, "Bridge wurde gestartet, 8 von 8 Werkzeugen sind bereit.", "Bridge started, 8 of 8 tools are ready."),
                    ExpectedToolCount);
                return 0;
            }
        }

        AppendLog("health_timeout", healthError);
        StopLaunchedBridge(launchOutput);
        WriteResponse(
            false,
            "failed",
            "health_timeout",
            Text(
                german,
                "Die Bridge wurde gestartet, erreichte aber nicht den Zustand 8 von 8. Prüfen Sie das Bridge-Protokoll.",
                "The bridge was started but did not reach the 8 of 8 ready state. Check the bridge log."),
            0);
        return 0;
    }

    private static void StopLaunchedBridge(string launchOutput)
    {
        Match pidMatch = Regex.Match(launchOutput ?? String.Empty, "\"pid\"\\s*:\\s*(?<pid>[0-9]+)");
        int pid;
        if (!pidMatch.Success || !Int32.TryParse(pidMatch.Groups["pid"].Value, out pid))
        {
            return;
        }

        try
        {
            using (Process process = Process.GetProcessById(pid))
            {
                process.Kill();
                process.WaitForExit(5000);
            }
        }
        catch
        {
        }

        try
        {
            if (
                File.Exists(BridgePidPath) &&
                String.Equals(File.ReadAllText(BridgePidPath).Trim(), pid.ToString(), StringComparison.Ordinal))
            {
                File.Delete(BridgePidPath);
            }
        }
        catch
        {
        }
    }

    private static Layout ResolveLayout()
    {
        string executableDirectory = AppDomain.CurrentDomain.BaseDirectory;
        string integrationRoot = Path.GetFullPath(Path.Combine(executableDirectory, "..", ".."));
        string bridgeEntry = Path.Combine(integrationRoot, "bridge", "dist", "src", "index.js");
        string healthScript = Path.Combine(integrationRoot, "bridge", "scripts", "healthcheck.mjs");
        string launchScript = Path.Combine(integrationRoot, "bridge", "scripts", "launch-bridge.mjs");
        string configPath = Environment.GetEnvironmentVariable("PLWC_CHAT_BRIDGE_CONFIG");

        if (String.IsNullOrWhiteSpace(configPath) || !File.Exists(configPath))
        {
            string installedConfig = Path.Combine(AppDataRoot, "config", "chat-bridge.json");
            configPath = File.Exists(installedConfig)
                ? installedConfig
                : Path.Combine(integrationRoot, "config", "plwc.example.json");
        }

        RequireFile(bridgeEntry, "bridge_files_missing");
        RequireFile(healthScript, "bridge_files_missing");
        RequireFile(launchScript, "bridge_files_missing");
        RequireFile(configPath, "bridge_config_missing");

        Layout layout = new Layout();
        layout.BridgeEntry = Path.GetFullPath(bridgeEntry);
        layout.ConfigPath = Path.GetFullPath(configPath);
        ResolveBridgeEndpoint(layout.ConfigPath, out layout.Endpoint, out layout.Port);
        layout.HealthScript = Path.GetFullPath(healthScript);
        layout.IntegrationRoot = integrationRoot;
        layout.LaunchScript = Path.GetFullPath(launchScript);
        return layout;
    }

    private static void ResolveBridgeEndpoint(string configPath, out string endpoint, out int port)
    {
        string json = File.ReadAllText(configPath);
        Match bridge = Regex.Match(
            json,
            "\"bridge\"\\s*:\\s*\\{(?<body>.*?)\\}",
            RegexOptions.Singleline);
        if (!bridge.Success)
        {
            throw new InvalidOperationException("bridge_config_invalid: bridge");
        }

        string body = bridge.Groups["body"].Value;
        Match hostMatch = Regex.Match(body, "\"host\"\\s*:\\s*\"(?<value>[^\"]+)\"");
        Match portMatch = Regex.Match(body, "\"port\"\\s*:\\s*(?<value>[0-9]+)");
        Match pathMatch = Regex.Match(body, "\"path\"\\s*:\\s*\"(?<value>/[^\"]*)\"");
        if (!hostMatch.Success || !portMatch.Success || !pathMatch.Success)
        {
            throw new InvalidOperationException("bridge_config_invalid: endpoint");
        }

        string host = hostMatch.Groups["value"].Value;
        int parsedPort;
        if (
            !String.Equals(host, "127.0.0.1", StringComparison.Ordinal) ||
            !Int32.TryParse(portMatch.Groups["value"].Value, out parsedPort) ||
            parsedPort < 1 ||
            parsedPort > 65535)
        {
            throw new InvalidOperationException("bridge_config_invalid: loopback");
        }

        port = parsedPort;
        endpoint = "ws://" + host + ":" + parsedPort + pathMatch.Groups["value"].Value;
    }

    private static void RequireFile(string path, string code)
    {
        if (!File.Exists(path))
        {
            throw new FileNotFoundException(code + ": " + Path.GetFileName(path));
        }
    }

    private static string ResolveNodePath()
    {
        List<string> candidates = new List<string>();
        AddNodeCandidate(candidates, Environment.GetEnvironmentVariable("PLWC_NODE_EXE"));
        AddConfiguredNodeCandidate(candidates);
        AddRegistryNodeCandidate(candidates, RegistryHive.LocalMachine, RegistryView.Registry64);
        AddRegistryNodeCandidate(candidates, RegistryHive.LocalMachine, RegistryView.Registry32);
        AddRegistryNodeCandidate(candidates, RegistryHive.CurrentUser, RegistryView.Default);
        AddNodeCandidate(candidates, Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
            "nodejs",
            "node.exe"));
        AddNodeCandidate(candidates, Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86),
            "nodejs",
            "node.exe"));
        AddNodeCandidate(candidates, Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "Programs",
            "nodejs",
            "node.exe"));

        string pathValue = Environment.GetEnvironmentVariable("PATH") ?? String.Empty;
        foreach (string pathEntry in pathValue.Split(Path.PathSeparator))
        {
            string cleaned = pathEntry.Trim().Trim('"');
            if (cleaned.Length > 0)
            {
                AddNodeCandidate(candidates, Path.Combine(cleaned, "node.exe"));
            }
        }

        foreach (string candidate in candidates)
        {
            if (File.Exists(candidate) && HasSupportedNodeVersion(candidate))
            {
                return Path.GetFullPath(candidate);
            }
        }
        return null;
    }

    private static void AddConfiguredNodeCandidate(List<string> candidates)
    {
        string settingsPath = Path.Combine(AppDataRoot, "config", "chat-bridge-launcher.json");
        if (!File.Exists(settingsPath))
        {
            return;
        }
        try
        {
            string source = File.ReadAllText(settingsPath);
            Match match = Regex.Match(source, "\"nodePath\"\\s*:\\s*\"(?<value>(?:\\\\.|[^\"])*)\"");
            if (match.Success)
            {
                AddNodeCandidate(candidates, Regex.Unescape(match.Groups["value"].Value));
            }
        }
        catch (Exception error)
        {
            AppendLog("settings_warning", error.Message);
        }
    }

    private static void AddRegistryNodeCandidate(
        List<string> candidates,
        RegistryHive hive,
        RegistryView view)
    {
        try
        {
            using (RegistryKey baseKey = RegistryKey.OpenBaseKey(hive, view))
            using (RegistryKey nodeKey = baseKey.OpenSubKey("SOFTWARE\\Node.js"))
            {
                if (nodeKey == null)
                {
                    return;
                }
                object installPath = nodeKey.GetValue("InstallPath");
                if (installPath != null)
                {
                    AddNodeCandidate(candidates, Path.Combine(installPath.ToString(), "node.exe"));
                }
            }
        }
        catch (Exception error)
        {
            AppendLog("registry_warning", error.Message);
        }
    }

    private static void AddNodeCandidate(List<string> candidates, string value)
    {
        if (String.IsNullOrWhiteSpace(value))
        {
            return;
        }
        string candidate = value.Trim().Trim('"');
        if (!Path.IsPathRooted(candidate))
        {
            return;
        }
        if (!candidates.Exists(delegate(string existing)
        {
            return String.Equals(existing, candidate, StringComparison.OrdinalIgnoreCase);
        }))
        {
            candidates.Add(candidate);
        }
    }

    private static bool HasSupportedNodeVersion(string nodePath)
    {
        string output;
        string error;
        int exitCode = RunProcess(nodePath, "--version", Path.GetDirectoryName(nodePath), 3000, out output, out error);
        Match version = Regex.Match(output, "^v(?<major>[0-9]+)\\.(?<minor>[0-9]+)");
        if (exitCode != 0 || !version.Success)
        {
            return false;
        }
        int major = Int32.Parse(version.Groups["major"].Value);
        int minor = Int32.Parse(version.Groups["minor"].Value);
        return major > 22 || (major == 22 && minor >= 12);
    }

    private static bool VerifyHealth(
        string nodePath,
        Layout layout,
        BuildIdentity buildIdentity,
        out string error)
    {
        List<string> failures = new List<string>();
        foreach (string origin in ApprovedWebSocketOrigins())
        {
            string output;
            string processError;
            int exitCode = RunProcess(
                nodePath,
                QuoteArgument(layout.HealthScript) +
                    " --endpoint " + QuoteArgument(layout.Endpoint) +
                    " --origin " + QuoteArgument(origin) +
                    " --expected-build-id " + QuoteArgument(buildIdentity.buildId) +
                    " --timeout-ms 2500",
                layout.IntegrationRoot,
                5000,
                out output,
                out processError);
            if (
                exitCode != 0 ||
                !Regex.IsMatch(output, "\"toolCount\"\\s*:\\s*" + ExpectedToolCount + "\\b") ||
                !HasJsonString(output, "buildId", buildIdentity.buildId) ||
                !HasJsonString(output, "nodeBridge", buildIdentity.components.nodeBridge) ||
                !HasJsonString(output, "browserExtension", buildIdentity.components.browserExtension) ||
                !HasJsonString(output, "nativeLauncher", buildIdentity.components.nativeLauncher))
            {
                failures.Add(origin + ": " + (processError + " " + output).Trim());
            }
        }
        error = String.Join("; ", failures.ToArray());
        return failures.Count == 0;
    }

    private static int RunProcess(
        string fileName,
        string arguments,
        string workingDirectory,
        int timeoutMilliseconds,
        out string output,
        out string error)
    {
        ProcessStartInfo startInfo = new ProcessStartInfo();
        startInfo.FileName = fileName;
        startInfo.Arguments = arguments;
        startInfo.WorkingDirectory = workingDirectory;
        startInfo.UseShellExecute = false;
        startInfo.CreateNoWindow = true;
        startInfo.WindowStyle = ProcessWindowStyle.Hidden;
        startInfo.RedirectStandardOutput = true;
        startInfo.RedirectStandardError = true;

        using (Process process = Process.Start(startInfo))
        {
            StringBuilder outputBuffer = new StringBuilder();
            StringBuilder errorBuffer = new StringBuilder();
            process.OutputDataReceived += delegate(object sender, DataReceivedEventArgs eventArgs)
            {
                if (eventArgs.Data != null)
                {
                    outputBuffer.AppendLine(eventArgs.Data);
                }
            };
            process.ErrorDataReceived += delegate(object sender, DataReceivedEventArgs eventArgs)
            {
                if (eventArgs.Data != null)
                {
                    errorBuffer.AppendLine(eventArgs.Data);
                }
            };
            process.BeginOutputReadLine();
            process.BeginErrorReadLine();
            if (!process.WaitForExit(timeoutMilliseconds))
            {
                try
                {
                    process.Kill();
                }
                catch
                {
                }
                process.WaitForExit();
                output = outputBuffer.ToString().Trim();
                error = ("Process timed out. " + errorBuffer.ToString()).Trim();
                return -1;
            }
            process.WaitForExit();
            output = outputBuffer.ToString().Trim();
            error = errorBuffer.ToString().Trim();
            return process.ExitCode;
        }
    }

    private static bool IsLoopbackPortOpen(int port)
    {
        try
        {
            using (TcpClient client = new TcpClient())
            {
                IAsyncResult result = client.BeginConnect("127.0.0.1", port, null, null);
                if (!result.AsyncWaitHandle.WaitOne(TimeSpan.FromMilliseconds(250)))
                {
                    return false;
                }
                client.EndConnect(result);
                return true;
            }
        }
        catch
        {
            return false;
        }
    }

    private static int RegisterNativeHost(string[] args)
    {
        bool german = IsGermanCommandLine(args);
        List<string> extensionIds = ApprovedExtensionIds();
        foreach (string requestedExtensionId in ArgumentValues(args, "--extension-id"))
        {
            if (!extensionIds.Contains(requestedExtensionId))
            {
                throw new InvalidOperationException(
                    "Unapproved PLwC extension ID: " + requestedExtensionId);
            }
        }

        string browser = ArgumentValue(args, "--browser") ?? "all";
        string manifestPath = NativeHostManifestPath();
        Directory.CreateDirectory(Path.GetDirectoryName(manifestPath));
        File.WriteAllText(
            manifestPath,
            BuildNativeManifest(Path.GetFullPath(Process.GetCurrentProcess().MainModule.FileName), extensionIds),
            new UTF8Encoding(false));

        foreach (string registryPath in BrowserRegistryPaths(browser))
        {
            using (RegistryKey key = Registry.CurrentUser.CreateSubKey(registryPath))
            {
                key.SetValue(String.Empty, manifestPath, RegistryValueKind.String);
            }
            AppendLog("registered", "HKCU\\" + registryPath + " -> " + manifestPath);
        }

        Console.WriteLine(Text(
            german,
            "PLwC Bridge-Einrichtung wurde registriert.",
            "PLwC Bridge Setup has been registered."));
        Console.WriteLine(manifestPath);
        return 0;
    }

    private static int UnregisterNativeHost(string[] args)
    {
        bool german = IsGermanCommandLine(args);
        string browser = ArgumentValue(args, "--browser") ?? "all";
        foreach (string registryPath in BrowserRegistryPaths(browser))
        {
            try
            {
                Registry.CurrentUser.DeleteSubKeyTree(registryPath, false);
                AppendLog("unregistered", "HKCU\\" + registryPath);
            }
            catch (ArgumentException)
            {
            }
        }
        Console.WriteLine(Text(
            german,
            "PLwC Bridge-Einrichtung wurde entfernt.",
            "PLwC Bridge Setup has been removed."));
        return 0;
    }

    private static int PrintRegistrationStatus(string[] args)
    {
        string browser = ArgumentValue(args, "--browser") ?? "all";
        bool registered = File.Exists(NativeHostManifestPath());
        foreach (string registryPath in BrowserRegistryPaths(browser))
        {
            using (RegistryKey key = Registry.CurrentUser.OpenSubKey(registryPath))
            {
                registered = registered && key != null &&
                    String.Equals(key.GetValue(String.Empty) as string, NativeHostManifestPath(), StringComparison.OrdinalIgnoreCase);
            }
        }
        Console.WriteLine("{\"registered\":" + (registered ? "true" : "false") +
            ",\"extensionId\":\"" + DevelopmentExtensionId +
            "\",\"extensionIds\":" + JsonStringArray(ApprovedExtensionIds()) +
            ",\"allowedOrigins\":" + JsonStringArray(ApprovedNativeMessagingOrigins()) +
            ",\"manifest\":\"" + EscapeJson(NativeHostManifestPath()) +
            "\",\"buildIdentity\":" + SerializeBuildIdentity(LoadBuildIdentity()) + "}");
        return registered ? 0 : 2;
    }

    private static string BuildNativeManifest(string launcherPath, List<string> extensionIds)
    {
        StringBuilder origins = new StringBuilder();
        for (int index = 0; index < extensionIds.Count; index++)
        {
            if (index > 0)
            {
                origins.Append(",");
            }
            origins.Append("\"chrome-extension://");
            origins.Append(EscapeJson(extensionIds[index]));
            origins.Append("/\"");
        }
        return "{" +
            "\"name\":\"" + NativeHostName + "\"," +
            "\"description\":\"Starts and verifies the local PLwC Chat Bridge.\"," +
            "\"path\":\"" + EscapeJson(launcherPath) + "\"," +
            "\"type\":\"stdio\"," +
            "\"allowed_origins\":[" + origins + "]" +
            "}";
    }

    private static List<string> ApprovedExtensionIds()
    {
        return new List<string>
        {
            DevelopmentExtensionId,
            ChromeStoreExtensionId,
            EdgeStoreExtensionId
        };
    }

    private static List<string> ApprovedNativeMessagingOrigins()
    {
        List<string> origins = new List<string>();
        foreach (string extensionId in ApprovedExtensionIds())
        {
            origins.Add("chrome-extension://" + extensionId + "/");
        }
        return origins;
    }

    private static List<string> ApprovedWebSocketOrigins()
    {
        List<string> origins = new List<string>();
        foreach (string extensionId in ApprovedExtensionIds())
        {
            origins.Add("chrome-extension://" + extensionId);
        }
        return origins;
    }

    private static string JsonStringArray(List<string> values)
    {
        StringBuilder builder = new StringBuilder("[");
        for (int index = 0; index < values.Count; index++)
        {
            if (index > 0)
            {
                builder.Append(",");
            }
            builder.Append("\"");
            builder.Append(EscapeJson(values[index]));
            builder.Append("\"");
        }
        builder.Append("]");
        return builder.ToString();
    }

    private static IEnumerable<string> BrowserRegistryPaths(string browser)
    {
        string normalized = browser.Trim().ToLowerInvariant();
        if (normalized == "chrome" || normalized == "both" || normalized == "all")
        {
            yield return "Software\\Google\\Chrome\\NativeMessagingHosts\\" + NativeHostName;
        }
        if (normalized == "edge" || normalized == "both" || normalized == "all")
        {
            yield return "Software\\Microsoft\\Edge\\NativeMessagingHosts\\" + NativeHostName;
        }
        if (normalized == "brave" || normalized == "all")
        {
            yield return "Software\\BraveSoftware\\Brave-Browser\\NativeMessagingHosts\\" + NativeHostName;
        }
        if (
            normalized != "chrome" &&
            normalized != "edge" &&
            normalized != "brave" &&
            normalized != "both" &&
            normalized != "all")
        {
            throw new InvalidOperationException("Unsupported browser selection: " + browser);
        }
    }

    private static string NativeHostManifestPath()
    {
        return Path.Combine(AppDataRoot, "config", "native-messaging", NativeHostName + ".json");
    }

    private static bool HasArgument(string[] args, string expected)
    {
        foreach (string argument in args)
        {
            if (String.Equals(argument, expected, StringComparison.OrdinalIgnoreCase))
            {
                return true;
            }
        }
        return false;
    }

    private static bool HasCommandLineMode(string[] args)
    {
        return HasArgument(args, "--register") ||
            HasArgument(args, "--unregister") ||
            HasArgument(args, "--status") ||
            HasArgument(args, "--build-identity");
    }

    private static string ArgumentValue(string[] args, string name)
    {
        for (int index = 0; index < args.Length - 1; index++)
        {
            if (String.Equals(args[index], name, StringComparison.OrdinalIgnoreCase))
            {
                return args[index + 1];
            }
        }
        return null;
    }

    private static List<string> ArgumentValues(string[] args, string name)
    {
        List<string> values = new List<string>();
        for (int index = 0; index < args.Length - 1; index++)
        {
            if (String.Equals(args[index], name, StringComparison.OrdinalIgnoreCase))
            {
                values.Add(args[index + 1].ToLowerInvariant());
            }
        }
        return values;
    }

    private static bool IsGermanCommandLine(string[] args)
    {
        string language = ArgumentValue(args, "--lang");
        if (!String.IsNullOrWhiteSpace(language))
        {
            return language.StartsWith("de", StringComparison.OrdinalIgnoreCase);
        }
        return Thread.CurrentThread.CurrentUICulture.TwoLetterISOLanguageName == "de";
    }

    private static string Text(bool german, string germanText, string englishText)
    {
        return german ? germanText : englishText;
    }

    private static string ReadMessage()
    {
        Stream input = Console.OpenStandardInput();
        byte[] lengthBytes = ReadExact(input, 4);
        int length = BitConverter.ToInt32(lengthBytes, 0);
        if (length <= 0 || length > MaxMessageBytes)
        {
            throw new InvalidOperationException("Native launcher request size is invalid.");
        }
        return Encoding.UTF8.GetString(ReadExact(input, length));
    }

    private static byte[] ReadExact(Stream stream, int count)
    {
        byte[] buffer = new byte[count];
        int offset = 0;
        while (offset < count)
        {
            int read = stream.Read(buffer, offset, count - offset);
            if (read == 0)
            {
                throw new EndOfStreamException("Native launcher request ended early.");
            }
            offset += read;
        }
        return buffer;
    }

    private static string QuoteArgument(string value)
    {
        return "\"" + value.Replace("\"", "\\\"") + "\"";
    }

    private static BuildIdentity LoadBuildIdentity()
    {
        using (Stream stream = Assembly.GetExecutingAssembly().GetManifestResourceStream(BuildIdentityResourceName))
        {
            if (stream == null)
            {
                throw new InvalidOperationException("Embedded PLwC Chat Bridge build identity is missing.");
            }
            using (StreamReader reader = new StreamReader(stream, new UTF8Encoding(false), true))
            {
                BuildIdentity identity = new JavaScriptSerializer().Deserialize<BuildIdentity>(reader.ReadToEnd());
                if (
                    identity == null ||
                    identity.schemaVersion != 1 ||
                    !String.Equals(identity.product, "PLwC Chat Bridge", StringComparison.Ordinal) ||
                    String.IsNullOrWhiteSpace(identity.releaseVersion) ||
                    !String.Equals(identity.buildId, "plwc-chat-bridge@" + identity.releaseVersion, StringComparison.Ordinal) ||
                    identity.installer == null ||
                    !String.Equals(identity.installer.componentId, "chat-bridge", StringComparison.Ordinal) ||
                    !String.Equals(identity.installer.directoryName, "bridge", StringComparison.Ordinal) ||
                    identity.components == null ||
                    String.IsNullOrWhiteSpace(identity.components.nodeBridge) ||
                    String.IsNullOrWhiteSpace(identity.components.browserExtension) ||
                    String.IsNullOrWhiteSpace(identity.components.nativeLauncher))
                {
                    throw new InvalidOperationException("Embedded PLwC Chat Bridge build identity is invalid.");
                }
                return identity;
            }
        }
    }

    private static string SerializeBuildIdentity(BuildIdentity identity)
    {
        return new JavaScriptSerializer().Serialize(identity);
    }

    private static string JsonStringValue(string json, string property)
    {
        Match match = Regex.Match(
            json,
            "\"" + Regex.Escape(property) + "\"\\s*:\\s*\"(?<value>(?:\\\\.|[^\"])*)\"");
        return match.Success ? Regex.Unescape(match.Groups["value"].Value) : null;
    }

    private static bool HasJsonString(string json, string property, string expected)
    {
        return String.Equals(JsonStringValue(json, property), expected, StringComparison.Ordinal);
    }

    private static void AppendLog(string state, string message)
    {
        try
        {
            Directory.CreateDirectory(LogRoot);
            string line = DateTimeOffset.Now.ToString("o") +
                " [" + state + "] " +
                message.Replace("\r", " ").Replace("\n", " ") +
                Environment.NewLine;
            File.AppendAllText(LauncherLogPath, line, new UTF8Encoding(false));
        }
        catch
        {
        }
    }

    private static void WriteResponse(
        bool ok,
        string state,
        string code,
        string message,
        int toolCount)
    {
        string json = "{\"ok\":" + (ok ? "true" : "false") +
            ",\"state\":\"" + EscapeJson(state) +
            "\",\"code\":\"" + EscapeJson(code) +
            "\",\"message\":\"" + EscapeJson(message) +
            "\",\"logPath\":\"" + EscapeJson(LauncherLogPath) +
            "\",\"toolCount\":" + toolCount +
            ",\"buildIdentity\":" + SerializeBuildIdentity(LoadBuildIdentity()) +
            "}";
        byte[] payload = Encoding.UTF8.GetBytes(json);
        byte[] length = BitConverter.GetBytes(payload.Length);
        Stream output = Console.OpenStandardOutput();
        output.Write(length, 0, length.Length);
        output.Write(payload, 0, payload.Length);
        output.Flush();
    }

    private static string EscapeJson(string value)
    {
        StringBuilder builder = new StringBuilder(value.Length);
        foreach (char character in value)
        {
            switch (character)
            {
                case '\\':
                    builder.Append("\\\\");
                    break;
                case '"':
                    builder.Append("\\\"");
                    break;
                case '\r':
                    builder.Append("\\r");
                    break;
                case '\n':
                    builder.Append("\\n");
                    break;
                case '\t':
                    builder.Append("\\t");
                    break;
                default:
                    if (character < 0x20)
                    {
                        builder.Append("\\u");
                        builder.Append(((int)character).ToString("x4"));
                    }
                    else
                    {
                        builder.Append(character);
                    }
                    break;
            }
        }
        return builder.ToString();
    }
}
