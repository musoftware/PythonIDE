"""Project templates that ``dotnet new`` does not have, written by RAD IDE like Visual Studio 2022 writes them.

``write(key, project_dir, name, framework) -> project file``:

* ``rad:shared-cs`` / ``rad:shared-vb``        Shared Project (radide/dotnet/shared/model.py)
* ``rad:netstd-cs`` / ``rad:netstd-vb``        Class Library (.NET Standard), SDK-style
* ``rad:fxlib-*`` / ``rad:fxconsole-*`` / ``rad:fxwinforms-*``  old-style (non-SDK) .NET Framework projects
* ``rad:fxwpf-cs``                             WPF App (.NET Framework)
* ``rad:fxservice-cs``                         Windows Service (.NET Framework)

Files are UTF-8 with BOM and CRLF (what Visual Studio writes).
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

CS_GUID = "{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}"
WPF_GUID = "{60dc8134-eba5-43b8-bcc9-bb4bc16c2548}"


def _guid() -> str:
    return "{" + str(uuid.uuid4()).upper() + "}"


def _ns(name: str) -> str:
    ns = re.sub(r"[^A-Za-z0-9_.]", "_", name)
    return ("_" + ns) if ns[:1].isdigit() else ns


def _write(folder: Path, rel: str, text: str, bom: bool = True) -> Path:
    p = folder / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    data = text.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")
    p.write_bytes((b"\xef\xbb\xbf" if bom else b"") + data)
    return p


def _sku(fw: str) -> str:
    return ".NETFramework,Version=" + fw


APP_CONFIG = """<?xml version="1.0" encoding="utf-8" ?>
<configuration>
    <startup>
        <supportedRuntime version="v4.0" sku="{sku}" />
    </startup>
</configuration>
"""

ASSEMBLY_INFO_CS = """using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
{extra_using}
// General Information about an assembly is controlled through the following
// set of attributes. Change these attribute values to modify the information
// associated with an assembly.
[assembly: AssemblyTitle("{name}")]
[assembly: AssemblyDescription("")]
[assembly: AssemblyConfiguration("")]
[assembly: AssemblyCompany("")]
[assembly: AssemblyProduct("{name}")]
[assembly: AssemblyCopyright("Copyright ©  {year}")]
[assembly: AssemblyTrademark("")]
[assembly: AssemblyCulture("")]

// Setting ComVisible to false makes the types in this assembly not visible
// to COM components.  If you need to access a type in this assembly from
// COM, set the ComVisible attribute to true on that type.
[assembly: ComVisible(false)]

// The following GUID is for the ID of the typelib if this project is exposed to COM
[assembly: Guid("{typelib}")]
{extra}
// Version information for an assembly consists of the following four values:
//
//      Major Version
//      Minor Version
//      Build Number
//      Revision
//
[assembly: AssemblyVersion("1.0.0.0")]
[assembly: AssemblyFileVersion("1.0.0.0")]
"""

ASSEMBLY_INFO_VB = """Imports System
Imports System.Reflection
Imports System.Runtime.InteropServices

' General Information about an assembly is controlled through the following
' set of attributes. Change these attribute values to modify the information
' associated with an assembly.

' Review the values of the assembly attributes

<Assembly: AssemblyTitle("{name}")>
<Assembly: AssemblyDescription("")>
<Assembly: AssemblyCompany("")>
<Assembly: AssemblyProduct("{name}")>
<Assembly: AssemblyCopyright("Copyright ©  {year}")>
<Assembly: AssemblyTrademark("")>

<Assembly: ComVisible(False)>

'The following GUID is for the ID of the typelib if this project is exposed to COM
<Assembly: Guid("{typelib}")>

' Version information for an assembly consists of the following four values:
'
'      Major Version
'      Minor Version
'      Build Number
'      Revision
'
<Assembly: AssemblyVersion("1.0.0.0")>
<Assembly: AssemblyFileVersion("1.0.0.0")>
"""

CS_PROJ = """<?xml version="1.0" encoding="utf-8"?>
<Project ToolsVersion="15.0" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
  <Import Project="$(MSBuildExtensionsPath)\\$(MSBuildToolsVersion)\\Microsoft.Common.props" Condition="Exists('$(MSBuildExtensionsPath)\\$(MSBuildToolsVersion)\\Microsoft.Common.props')" />
  <PropertyGroup>
    <Configuration Condition=" '$(Configuration)' == '' ">Debug</Configuration>
    <Platform Condition=" '$(Platform)' == '' ">AnyCPU</Platform>
    <ProjectGuid>{guid}</ProjectGuid>
    <OutputType>{output}</OutputType>
{extra_props}    <RootNamespace>{ns}</RootNamespace>
    <AssemblyName>{name}</AssemblyName>
    <TargetFrameworkVersion>{fw}</TargetFrameworkVersion>
    <FileAlignment>512</FileAlignment>
{tail_props}    <Deterministic>true</Deterministic>
  </PropertyGroup>
  <PropertyGroup Condition=" '$(Configuration)|$(Platform)' == 'Debug|AnyCPU' ">
    <PlatformTarget>AnyCPU</PlatformTarget>
    <DebugSymbols>true</DebugSymbols>
    <DebugType>full</DebugType>
    <Optimize>false</Optimize>
    <OutputPath>bin\\Debug\\</OutputPath>
    <DefineConstants>DEBUG;TRACE</DefineConstants>
    <ErrorReport>prompt</ErrorReport>
    <WarningLevel>4</WarningLevel>
  </PropertyGroup>
  <PropertyGroup Condition=" '$(Configuration)|$(Platform)' == 'Release|AnyCPU' ">
    <PlatformTarget>AnyCPU</PlatformTarget>
    <DebugType>pdbonly</DebugType>
    <Optimize>true</Optimize>
    <OutputPath>bin\\Release\\</OutputPath>
    <DefineConstants>TRACE</DefineConstants>
    <ErrorReport>prompt</ErrorReport>
    <WarningLevel>4</WarningLevel>
  </PropertyGroup>
  <ItemGroup>
{refs}  </ItemGroup>
{items}  <Import Project="$(MSBuildToolsPath)\\Microsoft.CSharp.targets" />
</Project>
"""

VB_PROJ = """<?xml version="1.0" encoding="utf-8"?>
<Project ToolsVersion="15.0" DefaultTargets="Build" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
  <Import Project="$(MSBuildExtensionsPath)\\$(MSBuildToolsVersion)\\Microsoft.Common.props" Condition="Exists('$(MSBuildExtensionsPath)\\$(MSBuildToolsVersion)\\Microsoft.Common.props')" />
  <PropertyGroup>
    <Configuration Condition=" '$(Configuration)' == '' ">Debug</Configuration>
    <Platform Condition=" '$(Platform)' == '' ">AnyCPU</Platform>
    <ProjectGuid>{guid}</ProjectGuid>
    <OutputType>{output}</OutputType>
{extra_props}    <RootNamespace>{ns}</RootNamespace>
    <AssemblyName>{name}</AssemblyName>
    <FileAlignment>512</FileAlignment>
    <MyType>{mytype}</MyType>
    <TargetFrameworkVersion>{fw}</TargetFrameworkVersion>
{tail_props}    <Deterministic>true</Deterministic>
  </PropertyGroup>
  <PropertyGroup Condition=" '$(Configuration)|$(Platform)' == 'Debug|AnyCPU' ">
    <PlatformTarget>AnyCPU</PlatformTarget>
    <DebugSymbols>true</DebugSymbols>
    <DebugType>full</DebugType>
    <DefineDebug>true</DefineDebug>
    <DefineTrace>true</DefineTrace>
    <OutputPath>bin\\Debug\\</OutputPath>
    <DocumentationFile>{name}.xml</DocumentationFile>
    <NoWarn>42016,41999,42017,42018,42019,42032,42036,42020,42021,42022</NoWarn>
  </PropertyGroup>
  <PropertyGroup Condition=" '$(Configuration)|$(Platform)' == 'Release|AnyCPU' ">
    <PlatformTarget>AnyCPU</PlatformTarget>
    <DebugType>pdbonly</DebugType>
    <DefineDebug>false</DefineDebug>
    <DefineTrace>true</DefineTrace>
    <Optimize>true</Optimize>
    <OutputPath>bin\\Release\\</OutputPath>
    <DocumentationFile>{name}.xml</DocumentationFile>
    <NoWarn>42016,41999,42017,42018,42019,42032,42036,42020,42021,42022</NoWarn>
  </PropertyGroup>
  <PropertyGroup>
    <OptionExplicit>On</OptionExplicit>
  </PropertyGroup>
  <PropertyGroup>
    <OptionCompare>Binary</OptionCompare>
  </PropertyGroup>
  <PropertyGroup>
    <OptionStrict>Off</OptionStrict>
  </PropertyGroup>
  <PropertyGroup>
    <OptionInfer>On</OptionInfer>
  </PropertyGroup>
  <ItemGroup>
{refs}  </ItemGroup>
  <ItemGroup>
{imports}  </ItemGroup>
{items}  <Import Project="$(MSBuildToolsPath)\\Microsoft.VisualBasic.targets" />
</Project>
"""

BASE_REFS_CS = ["System", "System.Core", "System.Xml.Linq", "System.Data.DataSetExtensions", "Microsoft.CSharp",
                "System.Data", "System.Net.Http", "System.Xml"]
BASE_REFS_VB = ["System", "System.Data", "System.Deployment", "System.Xml", "System.Core", "System.Xml.Linq",
                "System.Data.DataSetExtensions", "System.Net.Http"]
VB_IMPORTS = ["Microsoft.VisualBasic", "System", "System.Collections", "System.Collections.Generic", "System.Data",
              "System.Diagnostics", "System.Linq", "System.Xml.Linq", "System.Threading.Tasks"]


def _items_block(groups: list[list[str]]) -> str:
    out = ""
    for g in groups:
        if g:
            out += "  <ItemGroup>\n" + "".join(f"    {ln}\n" for ln in g) + "  </ItemGroup>\n"
    return out


def _refs(names: list[str]) -> str:
    return "".join(f'    <Reference Include="{n}" />\n' for n in names)


def _year() -> int:
    import datetime
    return datetime.date.today().year


# ============================================================================ C# (.NET Framework)
def _cs_project(folder: Path, name: str, fw: str, output: str, refs: list[str], groups: list[list[str]],
                extra_props: str = "", tail_props: str = "") -> Path:
    text = CS_PROJ.format(guid=_guid(), output=output, ns=_ns(name), name=name, fw=fw, refs=_refs(refs),
                          items=_items_block(groups), extra_props=extra_props, tail_props=tail_props)
    return _write(folder, f"{name}.csproj", text)


def _cs_assembly_info(folder: Path, name: str, extra: str = "", extra_using: str = "") -> None:
    _write(folder, "Properties/AssemblyInfo.cs",
           ASSEMBLY_INFO_CS.format(name=name, year=_year(), typelib=str(uuid.uuid4()), extra=extra,
                                   extra_using=extra_using))


def fx_library_cs(folder: Path, name: str, fw: str) -> Path:
    ns = _ns(name)
    _write(folder, "Class1.cs", "using System;\nusing System.Collections.Generic;\nusing System.Linq;\nusing System.Text;\n"
           f"using System.Threading.Tasks;\n\nnamespace {ns}\n{{\n    public class Class1\n    {{\n    }}\n}}\n")
    _cs_assembly_info(folder, name)
    return _cs_project(folder, name, fw, "Library", BASE_REFS_CS,
                       [['<Compile Include="Class1.cs" />', '<Compile Include="Properties\\AssemblyInfo.cs" />']])


def fx_console_cs(folder: Path, name: str, fw: str) -> Path:
    ns = _ns(name)
    _write(folder, "Program.cs", "using System;\nusing System.Collections.Generic;\nusing System.Linq;\nusing System.Text;\n"
           f"using System.Threading.Tasks;\n\nnamespace {ns}\n{{\n    internal class Program\n    {{\n"
           "        static void Main(string[] args)\n        {\n        }\n    }\n}\n")
    _write(folder, "App.config", APP_CONFIG.format(sku=_sku(fw)))
    _cs_assembly_info(folder, name)
    return _cs_project(folder, name, fw, "Exe", BASE_REFS_CS,
                       [['<Compile Include="Program.cs" />', '<Compile Include="Properties\\AssemblyInfo.cs" />'],
                        ['<None Include="App.config" />']],
                       tail_props="    <AutoGenerateBindingRedirects>true</AutoGenerateBindingRedirects>\n")


def fx_winforms_cs(folder: Path, name: str, fw: str) -> Path:
    ns = _ns(name)
    _write(folder, "Program.cs", "using System;\nusing System.Collections.Generic;\nusing System.Linq;\n"
           f"using System.Threading.Tasks;\nusing System.Windows.Forms;\n\nnamespace {ns}\n{{\n"
           "    internal static class Program\n    {\n        /// <summary>\n"
           "        /// The main entry point for the application.\n        /// </summary>\n"
           "        [STAThread]\n        static void Main()\n        {\n"
           "            Application.EnableVisualStyles();\n"
           "            Application.SetCompatibleTextRenderingDefault(false);\n"
           "            Application.Run(new Form1());\n        }\n    }\n}\n")
    _write(folder, "Form1.cs", "using System;\nusing System.Collections.Generic;\nusing System.ComponentModel;\n"
           "using System.Data;\nusing System.Drawing;\nusing System.Linq;\nusing System.Text;\n"
           f"using System.Threading.Tasks;\nusing System.Windows.Forms;\n\nnamespace {ns}\n{{\n"
           "    public partial class Form1 : Form\n    {\n        public Form1()\n        {\n"
           "            InitializeComponent();\n        }\n    }\n}\n")
    _write(folder, "Form1.Designer.cs", f"namespace {ns}\n{{\n    partial class Form1\n    {{\n"
           "        /// <summary>\n        /// Required designer variable.\n        /// </summary>\n"
           "        private System.ComponentModel.IContainer components = null;\n\n"
           "        /// <summary>\n        /// Clean up any resources being used.\n        /// </summary>\n"
           "        /// <param name=\"disposing\">true if managed resources should be disposed; otherwise, false.</param>\n"
           "        protected override void Dispose(bool disposing)\n        {\n"
           "            if (disposing && (components != null))\n            {\n                components.Dispose();\n"
           "            }\n            base.Dispose(disposing);\n        }\n\n"
           "        #region Windows Form Designer generated code\n\n        /// <summary>\n"
           "        /// Required method for Designer support - do not modify\n"
           "        /// the contents of this method with the code editor.\n        /// </summary>\n"
           "        private void InitializeComponent()\n        {\n"
           "            this.components = new System.ComponentModel.Container();\n"
           "            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;\n"
           "            this.ClientSize = new System.Drawing.Size(800, 450);\n"
           "            this.Text = \"Form1\";\n        }\n\n        #endregion\n    }\n}\n\n")
    _write(folder, "App.config", APP_CONFIG.format(sku=_sku(fw)))
    _cs_assembly_info(folder, name)
    refs = ["System", "System.Core", "System.Xml.Linq", "System.Data.DataSetExtensions", "Microsoft.CSharp",
            "System.Data", "System.Deployment", "System.Drawing", "System.Net.Http", "System.Windows.Forms",
            "System.Xml"]
    return _cs_project(folder, name, fw, "WinExe", refs,
                       [['<Compile Include="Form1.cs">', '  <SubType>Form</SubType>', '</Compile>',
                         '<Compile Include="Form1.Designer.cs">', '  <DependentUpon>Form1.cs</DependentUpon>',
                         '</Compile>', '<Compile Include="Program.cs" />',
                         '<Compile Include="Properties\\AssemblyInfo.cs" />'],
                        ['<None Include="App.config" />']],
                       tail_props="    <AutoGenerateBindingRedirects>true</AutoGenerateBindingRedirects>\n")


def fx_wpf_cs(folder: Path, name: str, fw: str) -> Path:
    ns = _ns(name)
    _write(folder, "App.xaml", f'<Application x:Class="{ns}.App"\n'
           '             xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"\n'
           '             xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"\n'
           f'             xmlns:local="clr-namespace:{ns}"\n             StartupUri="MainWindow.xaml">\n'
           '    <Application.Resources>\n         \n    </Application.Resources>\n</Application>\n')
    _write(folder, "App.xaml.cs", "using System;\nusing System.Collections.Generic;\nusing System.Configuration;\n"
           "using System.Data;\nusing System.Linq;\nusing System.Threading.Tasks;\nusing System.Windows;\n\n"
           f"namespace {ns}\n{{\n    /// <summary>\n    /// Interaction logic for App.xaml\n    /// </summary>\n"
           "    public partial class App : Application\n    {\n    }\n}\n")
    _write(folder, "MainWindow.xaml", f'<Window x:Class="{ns}.MainWindow"\n'
           '        xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"\n'
           '        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"\n'
           '        xmlns:d="http://schemas.microsoft.com/expression/blend/2008"\n'
           '        xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"\n'
           f'        xmlns:local="clr-namespace:{ns}"\n        mc:Ignorable="d"\n'
           '        Title="MainWindow" Height="450" Width="800">\n    <Grid>\n\n    </Grid>\n</Window>\n')
    _write(folder, "MainWindow.xaml.cs", "using System;\nusing System.Collections.Generic;\nusing System.Linq;\n"
           "using System.Text;\nusing System.Threading.Tasks;\nusing System.Windows;\nusing System.Windows.Controls;\n"
           "using System.Windows.Data;\nusing System.Windows.Documents;\nusing System.Windows.Input;\n"
           "using System.Windows.Media;\nusing System.Windows.Media.Imaging;\nusing System.Windows.Navigation;\n"
           f"using System.Windows.Shapes;\n\nnamespace {ns}\n{{\n    /// <summary>\n"
           "    /// Interaction logic for MainWindow.xaml\n    /// </summary>\n"
           "    public partial class MainWindow : Window\n    {\n        public MainWindow()\n        {\n"
           "            InitializeComponent();\n        }\n    }\n}\n")
    _write(folder, "App.config", APP_CONFIG.format(sku=_sku(fw)))
    _cs_assembly_info(folder, name, extra_using="using System.Windows;\n",
                      extra="\n[assembly: ThemeInfo(\n    ResourceDictionaryLocation.None, //where theme specific "
                            "resource dictionaries are located\n    ResourceDictionaryLocation.SourceAssembly //where the "
                            "generic resource dictionary is located\n)]\n")
    refs = ["System", "System.Data", "System.Xml", "Microsoft.CSharp", "System.Core", "System.Xml.Linq",
            "System.Data.DataSetExtensions", "System.Net.Http", "System.Xaml", "WindowsBase", "PresentationCore",
            "PresentationFramework"]
    text_refs = _refs(refs).replace('<Reference Include="System.Xaml" />',
                                    '<Reference Include="System.Xaml">\n      <RequiredTargetFramework>4.0'
                                    '</RequiredTargetFramework>\n    </Reference>')
    groups = [['<ApplicationDefinition Include="App.xaml">', '  <Generator>MSBuild:Compile</Generator>',
               '  <SubType>Designer</SubType>', '</ApplicationDefinition>',
               '<Page Include="MainWindow.xaml">', '  <Generator>MSBuild:Compile</Generator>',
               '  <SubType>Designer</SubType>', '</Page>',
               '<Compile Include="App.xaml.cs">', '  <DependentUpon>App.xaml</DependentUpon>',
               '  <SubType>Code</SubType>', '</Compile>',
               '<Compile Include="MainWindow.xaml.cs">', '  <DependentUpon>MainWindow.xaml</DependentUpon>',
               '  <SubType>Code</SubType>', '</Compile>'],
              ['<Compile Include="Properties\\AssemblyInfo.cs">', '  <SubType>Code</SubType>', '</Compile>'],
              ['<None Include="App.config" />']]
    text = CS_PROJ.format(guid=_guid(), output="WinExe", ns=ns, name=name, fw=fw, refs=text_refs,
                          items=_items_block(groups), extra_props="",
                          tail_props=f"    <ProjectTypeGuids>{WPF_GUID};{CS_GUID}</ProjectTypeGuids>\n"
                                     "    <WarningLevel>4</WarningLevel>\n"
                                     "    <AutoGenerateBindingRedirects>true</AutoGenerateBindingRedirects>\n")
    return _write(folder, f"{name}.csproj", text)


def fx_service_cs(folder: Path, name: str, fw: str) -> Path:
    ns = _ns(name)
    _write(folder, "Program.cs", "using System;\nusing System.Collections.Generic;\nusing System.Linq;\n"
           "using System.ServiceProcess;\nusing System.Text;\nusing System.Threading.Tasks;\n\n"
           f"namespace {ns}\n{{\n    internal static class Program\n    {{\n        /// <summary>\n"
           "        /// The main entry point for the application.\n        /// </summary>\n"
           "        static void Main()\n        {\n            ServiceBase[] ServicesToRun;\n"
           "            ServicesToRun = new ServiceBase[]\n            {\n                new Service1()\n"
           "            };\n            ServiceBase.Run(ServicesToRun);\n        }\n    }\n}\n")
    _write(folder, "Service1.cs", "using System;\nusing System.Collections.Generic;\nusing System.ComponentModel;\n"
           "using System.Data;\nusing System.Diagnostics;\nusing System.Linq;\nusing System.ServiceProcess;\n"
           f"using System.Text;\nusing System.Threading.Tasks;\n\nnamespace {ns}\n{{\n"
           "    public partial class Service1 : ServiceBase\n    {\n        public Service1()\n        {\n"
           "            InitializeComponent();\n        }\n\n        protected override void OnStart(string[] args)\n"
           "        {\n        }\n\n        protected override void OnStop()\n        {\n        }\n    }\n}\n")
    _write(folder, "Service1.Designer.cs", f"namespace {ns}\n{{\n    partial class Service1\n    {{\n"
           "        /// <summary> \n        /// Required designer variable.\n        /// </summary>\n"
           "        private System.ComponentModel.IContainer components = null;\n\n"
           "        /// <summary>\n        /// Clean up any resources being used.\n        /// </summary>\n"
           "        /// <param name=\"disposing\">true if managed resources should be disposed; otherwise, false.</param>\n"
           "        protected override void Dispose(bool disposing)\n        {\n"
           "            if (disposing && (components != null))\n            {\n                components.Dispose();\n"
           "            }\n            base.Dispose(disposing);\n        }\n\n"
           "        #region Component Designer generated code\n\n        /// <summary> \n"
           "        /// Required method for Designer support - do not modify \n"
           "        /// the contents of this method with the code editor.\n        /// </summary>\n"
           "        private void InitializeComponent()\n        {\n"
           "            components = new System.ComponentModel.Container();\n"
           "            this.ServiceName = \"Service1\";\n        }\n\n        #endregion\n    }\n}\n")
    _write(folder, "App.config", APP_CONFIG.format(sku=_sku(fw)))
    _cs_assembly_info(folder, name)
    refs = ["System", "System.Core", "System.Xml.Linq", "System.Data.DataSetExtensions", "Microsoft.CSharp",
            "System.Data", "System.Management", "System.Net.Http", "System.ServiceProcess", "System.Xml"]
    return _cs_project(folder, name, fw, "WinExe", refs,
                       [['<Compile Include="Program.cs" />', '<Compile Include="Properties\\AssemblyInfo.cs" />',
                         '<Compile Include="Service1.cs">', '  <SubType>Component</SubType>', '</Compile>',
                         '<Compile Include="Service1.Designer.cs">', '  <DependentUpon>Service1.cs</DependentUpon>',
                         '</Compile>'],
                        ['<None Include="App.config" />']],
                       tail_props="    <AutoGenerateBindingRedirects>true</AutoGenerateBindingRedirects>\n")


# ============================================================================ VB (.NET Framework)
def _vb_project(folder: Path, name: str, fw: str, output: str, mytype: str, refs: list[str], imports: list[str],
                groups: list[list[str]], extra_props: str = "", tail_props: str = "") -> Path:
    text = VB_PROJ.format(guid=_guid(), output=output, ns=_ns(name), name=name, fw=fw, mytype=mytype,
                          refs=_refs(refs), imports="".join(f'    <Import Include="{i}" />\n' for i in imports),
                          items=_items_block(groups), extra_props=extra_props, tail_props=tail_props)
    return _write(folder, f"{name}.vbproj", text)


def _vb_assembly_info(folder: Path, name: str) -> None:
    _write(folder, "My Project/AssemblyInfo.vb", ASSEMBLY_INFO_VB.format(name=name, year=_year(),
                                                                          typelib=str(uuid.uuid4())))


def fx_library_vb(folder: Path, name: str, fw: str) -> Path:
    _write(folder, "Class1.vb", "Public Class Class1\n\nEnd Class\n")
    _vb_assembly_info(folder, name)
    return _vb_project(folder, name, fw, "Library", "Windows", BASE_REFS_VB, VB_IMPORTS,
                       [['<Compile Include="Class1.vb" />', '<Compile Include="My Project\\AssemblyInfo.vb" />']])


def fx_console_vb(folder: Path, name: str, fw: str) -> Path:
    _write(folder, "Module1.vb", "Module Module1\n\n    Sub Main()\n\n    End Sub\n\nEnd Module\n")
    _write(folder, "App.config", APP_CONFIG.format(sku=_sku(fw)))
    _vb_assembly_info(folder, name)
    return _vb_project(folder, name, fw, "Exe", "Console", BASE_REFS_VB, VB_IMPORTS,
                       [['<Compile Include="Module1.vb" />', '<Compile Include="My Project\\AssemblyInfo.vb" />'],
                        ['<None Include="App.config" />']],
                       extra_props=f"    <StartupObject>{_ns(name)}.Module1</StartupObject>\n",
                       tail_props="    <AutoGenerateBindingRedirects>true</AutoGenerateBindingRedirects>\n")


def fx_winforms_vb(folder: Path, name: str, fw: str) -> Path:
    ns = _ns(name)
    _write(folder, "Form1.vb", "Public Class Form1\n\nEnd Class\n")
    _write(folder, "Form1.Designer.vb", "<Global.Microsoft.VisualBasic.CompilerServices.DesignerGenerated()> _\n"
           "Partial Class Form1\n    Inherits System.Windows.Forms.Form\n\n"
           "    'Form overrides dispose to clean up the component list.\n"
           "    <System.Diagnostics.DebuggerNonUserCode()> _\n"
           "    Protected Overrides Sub Dispose(ByVal disposing As Boolean)\n        Try\n"
           "            If disposing AndAlso components IsNot Nothing Then\n                components.Dispose()\n"
           "            End If\n        Finally\n            MyBase.Dispose(disposing)\n        End Try\n    End Sub\n\n"
           "    'Required by the Windows Form Designer\n    Private components As System.ComponentModel.IContainer\n\n"
           "    'NOTE: The following procedure is required by the Windows Form Designer\n"
           "    'It can be modified using the Windows Form Designer.  \n"
           "    'Do not modify it using the code editor.\n    <System.Diagnostics.DebuggerStepThrough()> _\n"
           "    Private Sub InitializeComponent()\n        components = New System.ComponentModel.Container()\n"
           "        Me.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font\n"
           "        Me.ClientSize = New System.Drawing.Size(800, 450)\n        Me.Text = \"Form1\"\n"
           "    End Sub\n\nEnd Class\n")
    _write(folder, "My Project/Application.myapp", '<?xml version="1.0" encoding="utf-8"?>\n'
           '<MyApplicationData xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
           'xmlns:xsd="http://www.w3.org/2001/XMLSchema">\n  <MySubMain>true</MySubMain>\n'
           '  <MainForm>Form1</MainForm>\n  <SingleInstance>false</SingleInstance>\n  <ShutdownMode>0</ShutdownMode>\n'
           '  <EnableVisualStyles>true</EnableVisualStyles>\n  <AuthenticationMode>0</AuthenticationMode>\n'
           '  <SaveMySettingsOnExit>true</SaveMySettingsOnExit>\n</MyApplicationData>\n')
    _write(folder, "My Project/Application.Designer.vb", "'" + "-" * 74 + "\n"
           "' <auto-generated>\n'     This code was generated by a tool.\n'\n"
           "'     Changes to this file may cause incorrect behavior and will be lost if\n"
           "'     the code is regenerated.\n' </auto-generated>\n'" + "-" * 74 + "\n\n"
           "Option Strict On\nOption Explicit On\n\n\nNamespace My\n\n"
           "    'NOTE: This file is auto-generated; do not modify it directly.  To make changes,\n"
           "    ' or if you encounter build errors in this file, go to the Project Designer\n"
           "    ' (go to Project Properties or double-click the My Project node in\n"
           "    ' Solution Explorer), and make changes on the Application tab.\n    '\n"
           "    Partial Friend Class MyApplication\n\n"
           "        <Global.System.Diagnostics.DebuggerStepThroughAttribute()>  _\n        Public Sub New()\n"
           "            MyBase.New(Global.Microsoft.VisualBasic.ApplicationServices.AuthenticationMode.Windows)\n"
           "            Me.IsSingleInstance = false\n            Me.EnableVisualStyles = true\n"
           "            Me.SaveMySettingsOnExit = true\n"
           "            Me.ShutDownStyle = Global.Microsoft.VisualBasic.ApplicationServices.ShutdownMode.AfterMainFormCloses\n"
           "        End Sub\n\n"
           "        <Global.System.Diagnostics.DebuggerStepThroughAttribute()>  _\n"
           "        Protected Overrides Sub OnCreateMainForm()\n"
           f"            Me.MainForm = Global.{ns}.Form1\n        End Sub\n    End Class\nEnd Namespace\n")
    _write(folder, "App.config", APP_CONFIG.format(sku=_sku(fw)))
    _vb_assembly_info(folder, name)
    refs = ["System", "System.Data", "System.Deployment", "System.Drawing", "System.Windows.Forms", "System.Xml",
            "System.Core", "System.Xml.Linq", "System.Data.DataSetExtensions", "System.Net.Http"]
    imports = VB_IMPORTS[:6] + ["System.Drawing", "System.Linq", "System.Xml.Linq", "System.Threading.Tasks",
                                "System.Windows.Forms"]
    return _vb_project(folder, name, fw, "WinExe", "WindowsForms", refs, imports,
                       [['<Compile Include="Form1.vb">', '  <SubType>Form</SubType>', '</Compile>',
                         '<Compile Include="Form1.Designer.vb">', '  <DependentUpon>Form1.vb</DependentUpon>',
                         '  <SubType>Form</SubType>', '</Compile>',
                         '<Compile Include="My Project\\Application.Designer.vb">', '  <AutoGen>True</AutoGen>',
                         '  <DependentUpon>Application.myapp</DependentUpon>', '  <DesignTime>True</DesignTime>',
                         '</Compile>', '<Compile Include="My Project\\AssemblyInfo.vb" />'],
                        ['<None Include="My Project\\Application.myapp">',
                         '  <Generator>MyApplicationCodeGenerator</Generator>',
                         '  <LastGenOutput>Application.Designer.vb</LastGenOutput>', '</None>',
                         '<None Include="App.config" />']],
                       extra_props=f"    <StartupObject>{ns}.My.MyApplication</StartupObject>\n",
                       tail_props="    <AutoGenerateBindingRedirects>true</AutoGenerateBindingRedirects>\n")


# ============================================================================ .NET Standard
def netstd_library(folder: Path, name: str, fw: str, language: str) -> Path:
    fw = fw or "netstandard2.0"
    if language == "VB":
        _write(folder, "Class1.vb", "Public Class Class1\n\nEnd Class\n")
        return _write(folder, f"{name}.vbproj", '<Project Sdk="Microsoft.NET.Sdk">\n\n  <PropertyGroup>\n'
                      f"    <RootNamespace>{_ns(name)}</RootNamespace>\n    <TargetFramework>{fw}</TargetFramework>\n"
                      "  </PropertyGroup>\n\n</Project>\n", bom=False)
    _write(folder, "Class1.cs", f"namespace {_ns(name)}\n{{\n    public class Class1\n    {{\n\n    }}\n}}\n")
    return _write(folder, f"{name}.csproj", '<Project Sdk="Microsoft.NET.Sdk">\n\n  <PropertyGroup>\n'
                  f"    <TargetFramework>{fw}</TargetFramework>\n  </PropertyGroup>\n\n</Project>\n", bom=False)


# ============================================================================ entry point
def write(key: str, folder: Path, name: str, framework: str = "") -> Path:
    """Write the template *key* into *folder* (created); returns the project file (.csproj/.vbproj/.shproj)."""
    folder = Path(folder)
    if key in ("rad:shared-cs", "rad:shared-vb"):
        from ..shared.model import create_shared_project
        return create_shared_project(folder, name, "C#" if key.endswith("cs") else "VB", own_folder=False).path
    folder.mkdir(parents=True, exist_ok=True)
    existing = [p for p in folder.glob(f"{name}.*proj")]
    if existing:
        raise ValueError(f"{existing[0]} already exists")
    fw = framework or "v4.8"
    table = {"rad:fxlib-cs": fx_library_cs, "rad:fxconsole-cs": fx_console_cs, "rad:fxwinforms-cs": fx_winforms_cs,
             "rad:fxwpf-cs": fx_wpf_cs, "rad:fxservice-cs": fx_service_cs, "rad:fxlib-vb": fx_library_vb,
             "rad:fxconsole-vb": fx_console_vb, "rad:fxwinforms-vb": fx_winforms_vb}
    if key in table:
        return table[key](folder, name, fw if fw.startswith("v") else "v4.8")
    if key in ("rad:netstd-cs", "rad:netstd-vb"):
        return netstd_library(folder, name, framework if framework.startswith("netstandard") else "netstandard2.0",
                              "VB" if key.endswith("vb") else "C#")
    raise ValueError(f"unknown RAD IDE template {key}")


__all__ = ["write", "netstd_library", "fx_library_cs", "fx_console_cs", "fx_winforms_cs", "fx_wpf_cs",
           "fx_service_cs", "fx_library_vb", "fx_console_vb", "fx_winforms_vb"]
