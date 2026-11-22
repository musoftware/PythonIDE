"""Static tables of the built-in quick fixes (used when no compiler metadata / language server answers)."""
from __future__ import annotations

# ============================================================================ Python
# common aliases -> import statement
PY_ALIASES = {
    "np": "import numpy as np", "pd": "import pandas as pd", "plt": "import matplotlib.pyplot as plt",
    "mpl": "import matplotlib as mpl", "sns": "import seaborn as sns", "tf": "import tensorflow as tf",
    "nn": "import torch.nn as nn", "F": "import torch.nn.functional as F", "sp": "import scipy as sp",
    "sm": "import statsmodels.api as sm", "px": "import plotly.express as px", "go": "import plotly.graph_objects as go",
    "tk": "import tkinter as tk", "ttk": "from tkinter import ttk", "mb": "from tkinter import messagebox as mb",
    "messagebox": "from tkinter import messagebox", "filedialog": "from tkinter import filedialog",
    "dt": "import datetime as dt", "xr": "import xarray as xr", "pl": "import polars as pl", "st": "import streamlit as st",
    "gpd": "import geopandas as gpd", "nx": "import networkx as nx", "cv": "import cv2 as cv", "jnp": "import jax.numpy as jnp",
    "ET": "import xml.etree.ElementTree as ET", "mp": "import multiprocessing as mp",
}
# names of the standard library -> module (from <module> import <name>)
PY_STDLIB_NAMES = {
    "Path": "pathlib", "PurePath": "pathlib", "defaultdict": "collections", "Counter": "collections",
    "OrderedDict": "collections", "deque": "collections", "namedtuple": "collections", "ChainMap": "collections",
    "dataclass": "dataclasses", "field": "dataclasses", "asdict": "dataclasses", "datetime": "datetime",
    "date": "datetime", "timedelta": "datetime", "timezone": "datetime", "partial": "functools",
    "lru_cache": "functools", "cache": "functools", "reduce": "functools", "wraps": "functools",
    "cached_property": "functools", "total_ordering": "functools", "Enum": "enum", "IntEnum": "enum", "auto": "enum",
    "Flag": "enum", "Optional": "typing", "List": "typing", "Dict": "typing", "Tuple": "typing", "Set": "typing",
    "Any": "typing", "Union": "typing", "Callable": "typing", "Iterable": "typing", "Iterator": "typing",
    "TypeVar": "typing", "Generic": "typing", "Protocol": "typing", "Literal": "typing", "cast": "typing",
    "TYPE_CHECKING": "typing", "Sequence": "typing", "Mapping": "typing", "ABC": "abc", "abstractmethod": "abc",
    "sleep": "time", "perf_counter": "time", "randint": "random", "choice": "random", "shuffle": "random",
    "uniform": "random", "sqrt": "math", "pi": "math", "floor": "math", "ceil": "math", "isclose": "math",
    "chain": "itertools", "product": "itertools", "permutations": "itertools", "combinations": "itertools",
    "groupby": "itertools", "islice": "itertools", "count": "itertools", "contextmanager": "contextlib",
    "suppress": "contextlib", "redirect_stdout": "contextlib", "ExitStack": "contextlib", "copy": "copy",
    "deepcopy": "copy", "pprint": "pprint", "dedent": "textwrap", "Decimal": "decimal",
    "Fraction": "fractions", "Thread": "threading", "Lock": "threading", "Event": "threading", "Queue": "queue",
    "ThreadPoolExecutor": "concurrent.futures", "ProcessPoolExecutor": "concurrent.futures",
    "as_completed": "concurrent.futures", "urlopen": "urllib.request", "urlencode": "urllib.parse",
    "urlparse": "urllib.parse", "quote": "urllib.parse", "glob": "glob", "fnmatch": "fnmatch", "which": "shutil",
    "rmtree": "shutil", "copyfile": "shutil", "TemporaryDirectory": "tempfile", "NamedTemporaryFile": "tempfile",
    "mkdtemp": "tempfile", "StringIO": "io", "BytesIO": "io", "ArgumentParser": "argparse", "uuid4": "uuid",
    "UUID": "uuid", "md5": "hashlib", "sha256": "hashlib", "b64encode": "base64", "b64decode": "base64",
    "SimpleNamespace": "types", "ModuleType": "types", "import_module": "importlib", "reload": "importlib",
    "getLogger": "logging", "mean": "statistics", "median": "statistics", "stdev": "statistics",
    "heappush": "heapq", "heappop": "heapq", "bisect_left": "bisect", "insort": "bisect", "zip_longest": "itertools",
    "accumulate": "itertools", "attrgetter": "operator", "itemgetter": "operator", "Popen": "subprocess",
    "run": "subprocess", "PIPE": "subprocess", "CalledProcessError": "subprocess",
}
# import name -> pip distribution (when they differ)
PY_DISTRIBUTIONS = {
    "cv2": "opencv-python", "PIL": "Pillow", "yaml": "PyYAML", "sklearn": "scikit-learn", "bs4": "beautifulsoup4",
    "skimage": "scikit-image", "dateutil": "python-dateutil", "dotenv": "python-dotenv", "jwt": "PyJWT",
    "serial": "pyserial", "usb": "pyusb", "Crypto": "pycryptodome", "OpenSSL": "pyOpenSSL", "magic": "python-magic",
    "docx": "python-docx", "pptx": "python-pptx", "fitz": "PyMuPDF", "win32api": "pywin32", "win32con": "pywin32",
    "win32gui": "pywin32", "pythoncom": "pywin32", "wx": "wxPython", "gi": "PyGObject", "attr": "attrs",
    "google.protobuf": "protobuf", "zmq": "pyzmq", "MySQLdb": "mysqlclient", "psycopg2": "psycopg2-binary",
    "telegram": "python-telegram-bot", "discord": "discord.py", "slugify": "python-slugify", "Levenshtein":
    "python-Levenshtein", "sentencepiece": "sentencepiece", "faiss": "faiss-cpu", "llama_cpp": "llama-cpp-python",
    "ruamel": "ruamel.yaml", "OpenGL": "PyOpenGL", "pygame": "pygame", "kivy": "kivy", "PySide6": "PySide6",
    "PyQt5": "PyQt5", "PyQt6": "PyQt6", "Image": "Pillow", "socks": "PySocks", "nacl": "PyNaCl", "lxml": "lxml",
    "markdown": "Markdown", "jinja2": "Jinja2", "flask": "Flask", "django": "Django", "fastapi": "fastapi",
    "uvicorn": "uvicorn", "pydantic": "pydantic", "sqlalchemy": "SQLAlchemy", "requests": "requests",
    "httpx": "httpx", "numpy": "numpy", "pandas": "pandas", "matplotlib": "matplotlib", "scipy": "scipy",
    "seaborn": "seaborn", "torch": "torch", "tensorflow": "tensorflow", "plotly": "plotly", "xlrd": "xlrd",
    "openpyxl": "openpyxl", "pyautogui": "PyAutoGUI", "pynput": "pynput", "keyboard": "keyboard", "psutil": "psutil",
    "tqdm": "tqdm", "rich": "rich", "click": "click", "typer": "typer", "pytest": "pytest", "toml": "toml",
    "tomli": "tomli", "ujson": "ujson", "orjson": "orjson", "speech_recognition": "SpeechRecognition",
    "pyttsx3": "pyttsx3", "gtts": "gTTS", "qrcode": "qrcode", "barcode": "python-barcode", "folium": "folium",
    "streamlit": "streamlit", "gradio": "gradio", "transformers": "transformers", "openai": "openai",
    "anthropic": "anthropic", "boto3": "boto3", "redis": "redis", "pymongo": "pymongo", "paramiko": "paramiko",
    "selenium": "selenium", "playwright": "playwright", "arabic_reshaper": "arabic-reshaper",
    "bidi": "python-bidi", "pyperclip": "pyperclip", "pymysql": "PyMySQL", "polars": "polars", "xarray": "xarray",
    "networkx": "networkx", "geopandas": "geopandas", "statsmodels": "statsmodels", "jax": "jax", "sympy": "sympy",
}

# ============================================================================ C# / VB.NET (fallback without SDK metadata)
CS_TYPES = {
    "List": "System.Collections.Generic", "Dictionary": "System.Collections.Generic",
    "HashSet": "System.Collections.Generic", "Queue": "System.Collections.Generic",
    "Stack": "System.Collections.Generic", "IEnumerable": "System.Collections.Generic",
    "IList": "System.Collections.Generic", "IDictionary": "System.Collections.Generic",
    "KeyValuePair": "System.Collections.Generic", "SortedDictionary": "System.Collections.Generic",
    "LinkedList": "System.Collections.Generic", "ArrayList": "System.Collections", "Hashtable": "System.Collections",
    "ObservableCollection": "System.Collections.ObjectModel", "ConcurrentDictionary": "System.Collections.Concurrent",
    "Enumerable": "System.Linq", "StringBuilder": "System.Text", "Encoding": "System.Text", "Regex": "System.Text.RegularExpressions",
    "Match": "System.Text.RegularExpressions", "File": "System.IO", "Directory": "System.IO", "Path": "System.IO",
    "StreamReader": "System.IO", "StreamWriter": "System.IO", "FileStream": "System.IO", "MemoryStream": "System.IO",
    "FileInfo": "System.IO", "DirectoryInfo": "System.IO", "Task": "System.Threading.Tasks",
    "Parallel": "System.Threading.Tasks", "Thread": "System.Threading", "CancellationToken": "System.Threading",
    "CancellationTokenSource": "System.Threading", "Interlocked": "System.Threading", "Mutex": "System.Threading",
    "HttpClient": "System.Net.Http", "HttpResponseMessage": "System.Net.Http", "WebClient": "System.Net",
    "IPAddress": "System.Net", "Dns": "System.Net", "TcpClient": "System.Net.Sockets", "Socket": "System.Net.Sockets",
    "JsonSerializer": "System.Text.Json", "JsonDocument": "System.Text.Json", "JsonElement": "System.Text.Json",
    "XmlDocument": "System.Xml", "XDocument": "System.Xml.Linq", "XElement": "System.Xml.Linq",
    "Stopwatch": "System.Diagnostics", "Process": "System.Diagnostics", "Debug": "System.Diagnostics",
    "Trace": "System.Diagnostics", "CultureInfo": "System.Globalization", "Assembly": "System.Reflection",
    "BindingFlags": "System.Reflection", "DataTable": "System.Data", "DataSet": "System.Data",
    "SqlConnection": "System.Data.SqlClient", "Color": "System.Drawing", "Point": "System.Drawing",
    "Size": "System.Drawing", "Rectangle": "System.Drawing", "Font": "System.Drawing", "Bitmap": "System.Drawing",
    "Graphics": "System.Drawing", "Brushes": "System.Drawing", "Pens": "System.Drawing",
    "MessageBox": "System.Windows.Forms", "Form": "System.Windows.Forms", "Button": "System.Windows.Forms",
    "TextBox": "System.Windows.Forms", "Label": "System.Windows.Forms", "Application": "System.Windows.Forms",
    "DialogResult": "System.Windows.Forms", "MessageBoxButtons": "System.Windows.Forms",
    "MessageBoxIcon": "System.Windows.Forms", "OpenFileDialog": "System.Windows.Forms",
    "SaveFileDialog": "System.Windows.Forms", "Timer": "System.Windows.Forms", "ListBox": "System.Windows.Forms",
    "ComboBox": "System.Windows.Forms", "DataGridView": "System.Windows.Forms", "Keys": "System.Windows.Forms",
    "Window": "System.Windows", "RoutedEventArgs": "System.Windows", "Visibility": "System.Windows",
    "DispatcherTimer": "System.Windows.Threading", "ICommand": "System.Windows.Input",
    "INotifyPropertyChanged": "System.ComponentModel", "PropertyChangedEventArgs": "System.ComponentModel",
    "CallerMemberName": "System.Runtime.CompilerServices", "Marshal": "System.Runtime.InteropServices",
    "DllImport": "System.Runtime.InteropServices", "StructLayout": "System.Runtime.InteropServices",
    "Interaction": "Microsoft.VisualBasic", "SHA256": "System.Security.Cryptography",
    "Aes": "System.Security.Cryptography", "RandomNumberGenerator": "System.Security.Cryptography",
    "Expression": "System.Linq.Expressions", "BigInteger": "System.Numerics", "Complex": "System.Numerics",
    "Vector2": "System.Numerics", "ImmutableList": "System.Collections.Immutable", "Channel": "System.Threading.Channels",
}
# WPF has its own MessageBox / Application / Window (System.Windows)
CS_WPF_ALTERNATIVES = {"MessageBox": "System.Windows", "Application": "System.Windows",
                       "Button": "System.Windows.Controls", "TextBox": "System.Windows.Controls",
                       "Label": "System.Windows.Controls", "ListBox": "System.Windows.Controls",
                       "ComboBox": "System.Windows.Controls", "Timer": "System.Timers"}
# RAD C# / GUI Bridge projects: the form is drawn by the IDE, the program is a console process; these WinForms /
# VB calls have a RAD helper (radide/runtimes/clients/csharp/Rad.cs - "global using static Rad")
RAD_CS_EQUIVALENTS = {
    "MessageBox": ("MsgBox", "MessageBox.Show"), "Interaction": ("InputBox", "Interaction.InputBox"),
    "Application": ("End", "Application.Exit"),
}

# ============================================================================ JavaScript / TypeScript
NODE_BUILTINS = {"assert", "async_hooks", "buffer", "child_process", "cluster", "console", "constants", "crypto",
                 "dgram", "diagnostics_channel", "dns", "domain", "events", "fs", "http", "http2", "https",
                 "inspector", "module", "net", "os", "path", "perf_hooks", "process", "punycode", "querystring",
                 "readline", "repl", "stream", "string_decoder", "sys", "timers", "tls", "trace_events", "tty",
                 "url", "util", "v8", "vm", "wasi", "worker_threads", "zlib", "test", "sqlite"}
# packages that ship their own types (no @types/... needed)
TYPED_PACKAGES = {"axios", "dayjs", "zod", "vue", "rxjs", "typeorm", "prisma", "@prisma/client", "vite", "vitest",
                  "date-fns", "luxon", "chalk", "commander", "yargs", "pinia", "svelte", "socket.io", "ws",
                  "playwright", "puppeteer", "mongoose", "sequelize", "knex", "electron", "three", "@angular/core"}

# ============================================================================ Rust
RUST_STD = {
    "HashMap": "std::collections::HashMap", "HashSet": "std::collections::HashSet",
    "BTreeMap": "std::collections::BTreeMap", "BTreeSet": "std::collections::BTreeSet",
    "VecDeque": "std::collections::VecDeque", "BinaryHeap": "std::collections::BinaryHeap",
    "Rc": "std::rc::Rc", "Weak": "std::rc::Weak", "RefCell": "std::cell::RefCell", "Cell": "std::cell::Cell",
    "Arc": "std::sync::Arc", "Mutex": "std::sync::Mutex", "RwLock": "std::sync::RwLock", "mpsc": "std::sync::mpsc",
    "AtomicUsize": "std::sync::atomic::AtomicUsize", "AtomicBool": "std::sync::atomic::AtomicBool",
    "File": "std::fs::File", "fs": "std::fs", "Path": "std::path::Path", "PathBuf": "std::path::PathBuf",
    "Read": "std::io::Read", "Write": "std::io::Write", "BufRead": "std::io::BufRead",
    "BufReader": "std::io::BufReader", "BufWriter": "std::io::BufWriter", "io": "std::io",
    "Duration": "std::time::Duration", "Instant": "std::time::Instant", "thread": "std::thread",
    "Ordering": "std::cmp::Ordering", "Reverse": "std::cmp::Reverse", "FromStr": "std::str::FromStr",
    "fmt": "std::fmt", "Display": "std::fmt::Display", "Debug": "std::fmt::Debug", "env": "std::env",
    "process": "std::process", "Command": "std::process::Command", "mem": "std::mem", "Cow": "std::borrow::Cow",
    "PhantomData": "std::marker::PhantomData", "Error": "std::error::Error", "TcpListener": "std::net::TcpListener",
    "TcpStream": "std::net::TcpStream", "Add": "std::ops::Add", "Deref": "std::ops::Deref",
    "Hash": "std::hash::Hash", "Hasher": "std::hash::Hasher", "Infallible": "std::convert::Infallible",
    "TryFrom": "std::convert::TryFrom", "Iterator": "std::iter::Iterator", "once": "std::iter::once",
}
RUST_BUILTIN_CRATES = {"std", "core", "alloc", "crate", "self", "super", "proc_macro", "test"}

# ============================================================================ Go
GO_STDLIB = {
    "fmt": "fmt", "os": "os", "strings": "strings", "strconv": "strconv", "time": "time", "math": "math",
    "sort": "sort", "errors": "errors", "io": "io", "bufio": "bufio", "bytes": "bytes", "sync": "sync",
    "context": "context", "http": "net/http", "json": "encoding/json", "filepath": "path/filepath",
    "path": "path", "regexp": "regexp", "log": "log", "exec": "os/exec", "unicode": "unicode", "utf8": "unicode/utf8",
    "rand": "math/rand", "atomic": "sync/atomic", "flag": "flag", "url": "net/url", "net": "net",
    "base64": "encoding/base64", "hex": "encoding/hex", "csv": "encoding/csv", "xml": "encoding/xml",
    "sha256": "crypto/sha256", "md5": "crypto/md5", "template": "text/template", "reflect": "reflect",
    "runtime": "runtime", "signal": "os/signal", "slices": "slices", "maps": "maps", "slog": "log/slog",
    "ioutil": "io/ioutil", "embed": "embed", "testing": "testing", "sql": "database/sql", "big": "math/big",
    "heap": "container/heap", "list": "container/list", "tabwriter": "text/tabwriter", "fs": "io/fs",
}

# ============================================================================ Java
JAVA_CLASSES = {
    **{n: "java.util" for n in ("List", "ArrayList", "LinkedList", "Map", "HashMap", "TreeMap", "LinkedHashMap",
                               "Set", "HashSet", "TreeSet", "LinkedHashSet", "Arrays", "Collections", "Scanner",
                               "Optional", "Objects", "Iterator", "Random", "Queue", "Deque", "ArrayDeque",
                               "PriorityQueue", "Stack", "Vector", "UUID", "Date", "Calendar", "Comparator",
                               "StringJoiner", "Locale", "Properties", "Timer", "TimerTask", "BitSet")},
    **{n: "java.io" for n in ("File", "IOException", "BufferedReader", "BufferedWriter", "InputStreamReader",
                             "FileReader", "FileWriter", "PrintWriter", "InputStream", "OutputStream",
                             "FileInputStream", "FileOutputStream", "Serializable", "UncheckedIOException",
                             "PrintStream", "StringReader", "StringWriter", "FileNotFoundException")},
    **{n: "java.nio.file" for n in ("Path", "Paths", "Files", "StandardOpenOption")},
    "StandardCharsets": "java.nio.charset", "Charset": "java.nio.charset",
    **{n: "java.time" for n in ("LocalDate", "LocalDateTime", "LocalTime", "Duration", "Instant", "ZonedDateTime",
                               "ZoneId", "Period")},
    "DateTimeFormatter": "java.time.format", "ChronoUnit": "java.time.temporal",
    **{n: "java.util.stream" for n in ("Collectors", "Stream", "IntStream", "LongStream", "DoubleStream")},
    **{n: "java.util.function" for n in ("Function", "Supplier", "Consumer", "Predicate", "BiFunction",
                                        "BiConsumer", "UnaryOperator", "BinaryOperator")},
    **{n: "java.util.concurrent" for n in ("ExecutorService", "Executors", "CompletableFuture", "Future",
                                          "ConcurrentHashMap", "TimeUnit", "CountDownLatch", "Callable",
                                          "CopyOnWriteArrayList", "ThreadLocalRandom")},
    "AtomicInteger": "java.util.concurrent.atomic", "AtomicLong": "java.util.concurrent.atomic",
    "AtomicBoolean": "java.util.concurrent.atomic", "ReentrantLock": "java.util.concurrent.locks",
    "Pattern": "java.util.regex", "Matcher": "java.util.regex", "BigDecimal": "java.math",
    "BigInteger": "java.math", "RoundingMode": "java.math",
    **{n: "javax.swing" for n in ("JFrame", "JButton", "JLabel", "JPanel", "JOptionPane", "SwingUtilities",
                                 "JTextField", "JTextArea", "JScrollPane", "JList", "JComboBox", "JCheckBox",
                                 "JMenuBar", "JMenu", "JMenuItem", "JFileChooser", "JTable", "ImageIcon")},
    **{n: "java.awt" for n in ("BorderLayout", "FlowLayout", "GridLayout", "Dimension", "Graphics", "Graphics2D",
                              "Font", "Toolkit")},
    "ActionEvent": "java.awt.event", "ActionListener": "java.awt.event", "MouseEvent": "java.awt.event",
    "KeyEvent": "java.awt.event", "URI": "java.net", "URL": "java.net", "HttpClient": "java.net.http",
    "HttpRequest": "java.net.http", "HttpResponse": "java.net.http", "Connection": "java.sql",
    "DriverManager": "java.sql", "PreparedStatement": "java.sql", "ResultSet": "java.sql", "SQLException": "java.sql",
}

# ============================================================================ PHP (composer)
PHP_PACKAGES = {
    "Monolog": "monolog/monolog", "GuzzleHttp": "guzzlehttp/guzzle", "Carbon": "nesbot/carbon",
    "PHPUnit": "phpunit/phpunit", "Dotenv": "vlucas/phpdotenv", "PHPMailer": "phpmailer/phpmailer",
    "Ramsey\\Uuid": "ramsey/uuid", "League\\Csv": "league/csv", "League\\Flysystem": "league/flysystem",
    "Twig": "twig/twig", "Doctrine\\DBAL": "doctrine/dbal", "Doctrine\\ORM": "doctrine/orm",
    "Firebase\\JWT": "firebase/php-jwt", "Intervention\\Image": "intervention/image",
    "PhpOffice\\PhpSpreadsheet": "phpoffice/phpspreadsheet", "Dompdf": "dompdf/dompdf", "Faker": "fakerphp/faker",
    "Predis": "predis/predis", "Psr\\Log": "psr/log", "Slim": "slim/slim", "Mockery": "mockery/mockery",
    "Illuminate\\Support": "illuminate/support", "Stripe": "stripe/stripe-php", "Aws": "aws/aws-sdk-php",
}

__all__ = ["PY_ALIASES", "PY_STDLIB_NAMES", "PY_DISTRIBUTIONS", "CS_TYPES", "CS_WPF_ALTERNATIVES",
           "RAD_CS_EQUIVALENTS", "NODE_BUILTINS", "TYPED_PACKAGES", "RUST_STD", "RUST_BUILTIN_CRATES", "GO_STDLIB",
           "JAVA_CLASSES", "PHP_PACKAGES"]
