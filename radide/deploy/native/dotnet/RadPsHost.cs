// RAD IDE - PowerShell host of the native WinForms runtime (radide/deploy/native/dotnet_winforms.py).
// The project's .ps1 files run in a Windows PowerShell 5.1 runspace inside this exe (System.Management.Automation
// is part of Windows); the forms are WinForms forms. The GUI Bridge client (Rad.ps1) is loaded unchanged and its
// RadSend / RadAsk are redirected here: the same SET/GET/CALL/MSGBOX/... lines, executed on the real controls.
#nullable disable
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Management.Automation;
using System.Management.Automation.Runspaces;
using System.Reflection;
using System.Text;

namespace RadNative
{
    public static class PsBridge
    {
        static string[] Split(string s, int n)
        {
            var parts = (s ?? "").Split(new[] { ' ' }, n);
            var out1 = new string[n];
            for (int i = 0; i < n; i++) out1[i] = i < parts.Length ? parts[i] : "";
            return out1;
        }

        /// <summary>One line of the GUI Bridge protocol (program -> host); returns the answer line.</summary>
        public static string Ask(string line)
        {
            line = line ?? "";
            var sp = line.IndexOf(' ');
            var cmd = (sp < 0 ? line : line.Substring(0, sp)).ToUpperInvariant();
            var rest = sp < 0 ? "" : line.Substring(sp + 1);
            switch (cmd)
            {
                case "SET": { var a = Split(rest, 3); RadApp.SetProp(a[0], a[1], a[2]); return ""; }
                case "GET": { var a = Split(rest, 2); return RadApp.GetProp(a[0], a[1]); }
                case "CALL":
                    {
                        var a = Split(rest, 3);
                        return RadApp.CallMethod(a[0], a[1], a[2].Length == 0 ? new string[0] : a[2].Split('\t'));
                    }
                case "MSGBOX": return RadApp.MsgBox(rest).ToString();
                case "INPUT": return RadApp.InputBox(rest);
                case "SHOW": RadApp.ShowForm(rest.Trim(), true); return "";
                case "HIDE": RadApp.ShowForm(rest.Trim(), false); return "";
                case "END": RadApp.End(); return "";
            }
            return "";
        }
    }

    public sealed class PsHost : IHandlers
    {
        readonly Runspace rs;
        readonly HashSet<string> names;
        int depth;          // > 0 while a handler runs: events it raises (Show -> Load ...) run as nested pipelines

        public PsHost(IEnumerable<string> handlers)
        {
            names = new HashSet<string>(handlers, StringComparer.OrdinalIgnoreCase);
            rs = RunspaceFactory.CreateRunspace();
            rs.ThreadOptions = PSThreadOptions.UseCurrentThread;     // handlers run on the UI thread
            rs.Open();
        }

        static string Resource(string name)
        {
            using (var s = Assembly.GetExecutingAssembly().GetManifestResourceStream(name))
            using (var r = new StreamReader(s, Encoding.UTF8))
                return r.ReadToEnd();
        }

        /// <summary>Run the embedded scripts (client, modules, designers, forms) in the global scope.</summary>
        public bool Load(string resource)
        {
            using (var ps = PowerShell.Create())
            {
                ps.Runspace = rs;
                ps.AddScript(Resource(resource), false);
                try { ps.Invoke(); }
                catch (RuntimeException ex) { RadApp.ReportError("", ex); return false; }
                if (ps.Streams.Error.Count > 0) Report("", ps.Streams.Error[0]);
            }
            return true;
        }

        static void Report(string where, ErrorRecord er)
        {
            var pos = er.InvocationInfo != null ? er.InvocationInfo.PositionMessage : "";
            RadApp.ReportError(where, new Exception(er.Exception.Message + (string.IsNullOrEmpty(pos) ? "" : "\r\n" + pos)));
        }

        public bool Has(string name) { return names.Contains(name); }

        public void Invoke(string name, RadEvent e)
        {
            var o = new PSObject();
            o.Properties.Add(new PSNoteProperty("Sender", e.Sender));
            o.Properties.Add(new PSNoteProperty("Name", e.Name));
            o.Properties.Add(new PSNoteProperty("Args", e.Args));
            o.Properties.Add(new PSNoteProperty("X", e.X));
            o.Properties.Add(new PSNoteProperty("Y", e.Y));
            o.Properties.Add(new PSNoteProperty("Button", e.Button));
            o.Properties.Add(new PSNoteProperty("KeyCode", e.KeyCode));
            o.Properties.Add(new PSNoteProperty("KeyChar", e.KeyChar));
            o.Properties.Add(new PSNoteProperty("Delta", e.Delta));
            o.Properties.Add(new PSNoteProperty("Cancel", false));
            using (var ps = depth > 0 ? PowerShell.Create(RunspaceMode.CurrentRunspace) : PowerShell.Create())
            {
                if (depth == 0) ps.Runspace = rs;
                ps.AddCommand(name).AddArgument(o);
                depth++;
                try { ps.Invoke(); }
                catch (RuntimeException ex)
                {
                    var er = ex.ErrorRecord;
                    if (er != null) Report(name, er); else RadApp.ReportError(name, ex);
                    return;
                }
                finally { depth--; }
                if (ps.HadErrors && ps.Streams.Error.Count > 0) Report(name, ps.Streams.Error[0]);
            }
            var c = o.Properties["Cancel"];
            if (c != null && c.Value is bool && (bool)c.Value) e.Cancel = true;
        }
    }
}
