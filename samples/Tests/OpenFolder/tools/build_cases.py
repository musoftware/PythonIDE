"""Hand-written project layouts + copies of samples for the Open Folder detection test."""
import json
import os
import tempfile
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = Path(os.environ.get("RADIDE_OPENDETECT_CASES") or (Path(tempfile.gettempdir()) / "radide_opendetect_cases"))
REPO = Path(__file__).resolve().parents[4]
SAMPLES = REPO / "samples"


def w(rel, text):
    p = CASES / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def fresh(name):
    d = CASES / name
    if d.exists():
        shutil.rmtree(d)
    return d


HAND = {
    "PhpPlain": {"index.php": "<?php echo 'Hello from PHP ' . PHP_VERSION; ?>\n", "about.php": "<p>About</p>\n"},
    "PhpPublic": {"composer.json": json.dumps({"require": {"php": ">=8.1"}}), "public/index.php":
                  "<?php echo 'public root';\n", "src/App.php": "<?php class App {}\n"},
    "WordPressSite": {"wp-config.php": "<?php define('DB_NAME','wp');\n", "index.php": "<?php echo 'wp';\n",
                      "wp-includes/version.php": "<?php $wp_version = '6.6.2';\n", "wp-admin/index.php": "<?php\n"},
    "SymfonyApp": {"composer.json": json.dumps({"require": {"php": ">=8.2", "symfony/framework-bundle": "7.1.*"}}),
                   "bin/console": "#!/usr/bin/env php\n<?php\n", "config/bundles.php": "<?php return [];\n",
                   "public/index.php": "<?php echo 'symfony';\n"},
    "StaticSite": {"index.html": "<!doctype html><title>Static</title><h1>Hello static</h1>\n",
                   "css/site.css": "body{}\n", "js/app.js": "console.log(1)\n"},
    "ExpressApi": {"package.json": json.dumps({"name": "express-api", "main": "server.js",
                                               "dependencies": {"express": "^4.19.2"}}),
                   "server.js": "const express=require('express');\n"},
    "NextApp": {"package.json": json.dumps({"name": "next-app", "scripts": {"dev": "next dev"},
                                            "dependencies": {"next": "15.0.0", "react": "19.0.0"}}),
                "app/page.js": "export default function P(){return 'hi'}\n"},
    "DjangoSite": {"manage.py": "import os\nos.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')\n",
                   "mysite/__init__.py": "", "mysite/settings.py": "DEBUG=True\n", "mysite/urls.py": "",
                   "requirements.txt": "Django>=5.1\n"},
    "FlaskMini": {"app.py": "from flask import Flask\napp = Flask(__name__)\n\n@app.route('/')\ndef i():\n"
                            "    return 'hi'\n", "requirements.txt": "flask\n"},
    "FastApiMini": {"main.py": "from fastapi import FastAPI\napi = FastAPI()\n", "requirements.txt": "fastapi\nuvicorn\n"},
    "PyTkApp": {"main.py": "import tkinter as tk\n\nif __name__ == '__main__':\n    print('Tk app starts')\n"
                           "    import sys\n    sys.exit(0)\n", "helpers.py": "def add(a, b):\n    return a + b\n"},
    "PyQtApp": {"app.py": "from PySide6.QtWidgets import QApplication\n\nif __name__ == '__main__':\n    pass\n"},
    "PyConsole": {"hello.py": "if __name__ == '__main__':\n    print('Hello from Python', 6 * 7)\n"},
    "PygameGame": {"game.py": "import pygame\n\nif __name__ == '__main__':\n    pygame.init()\n"},
    "JupyterNb": {"analysis.ipynb": json.dumps({"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}),
                  "data.ipynb": json.dumps({"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5})},
    "LooseC": {"main.c": "#include <stdio.h>\nint main(void){printf(\"hi\\n\");return 0;}\n",
               "util.c": "int add(int a,int b){return a+b;}\n", "util.h": "int add(int,int);\n"},
    "LooseCpp": {"main.cpp": "#include <iostream>\nint main(){std::cout<<\"hi\";}\n"},
    "MakeProj": {"Makefile": "all:\n\tgcc -o app main.c\n", "main.c": "int main(void){return 0;}\n"},
    "LooseCSharp": {"Program.cs": "using System;\nclass P { static void Main() { Console.WriteLine(\"Hello from loose C#\"); } }\n",
                    "Util.cs": "static class Util { public static int Add(int a,int b)=>a+b; }\n"},
    "LooseJava": {"Main.java": "public class Main { public static void main(String[] a){ System.out.println(\"hi\"); } }\n"},
    "RailsApp": {"Gemfile": "source 'https://rubygems.org'\ngem 'rails', '~> 7.2'\n",
                 "config/application.rb": "require_relative 'boot'\n", "app/models/user.rb": "class User; end\n"},
    "SinatraApp": {"Gemfile": "gem 'sinatra'\n", "app.rb": "require 'sinatra'\nget('/') { 'hi' }\n"},
    "RubyScripts": {"run.rb": "puts 'hi'\n"},
    "RingProg": {"main.ring": "func main\n  see 'hi' + nl\n", "lib.ring": "func add a, b return a+b\n"},
    "LuaScripts": {"main.lua": "print('hi')\n"},
    "PerlScripts": {"tool.pl": "print \"hi\\n\";\n"},
    "PsScripts": {"build.ps1": "Write-Host hi\n"},
    "FortranProg": {"main.f90": "program hello\n  print *, 'hi'\nend program hello\n"},
    "DartPkg": {"pubspec.yaml": "name: dartpkg\nenvironment:\n  sdk: ^3.0.0\n", "bin/main.dart": "void main() { print('hi'); }\n"},
    "GodotGame": {"project.godot": 'config_version=5\n[application]\nconfig/name="Dodge"\n'
                                   'config/features=PackedStringArray("4.3", "Forward Plus")\n',
                  "main.tscn": "[gd_scene format=3]\n", "player.gd": "extends Node2D\n"},
    "KotlinLoose": {"Main.kt": "fun main() = println(\"hi\")\n"},
    "VbNetLoose": {"Module1.vb": "Module Module1\nSub Main()\nEnd Sub\nEnd Module\n"},
    "VbBasModules": {"Module1.bas": "Attribute VB_Name = \"Module1\"\nSub Main()\n  Debug.Print \"hi\"\nEnd Sub\n"},
    "MavenSpring": {"pom.xml": "<project><parent><artifactId>spring-boot-starter-parent</artifactId></parent>"
                               "<dependencies><dependency><artifactId>spring-boot-starter-web</artifactId>"
                               "</dependency></dependencies></project>\n",
                    "src/main/java/App.java": "class App {}\n"},
    "EmptyFolder": {"notes.txt": "nothing here\n"},
    # multi-project: a PHP backend + a Flutter app + a static landing page
    "MultiRepo": {"README.md": "# repo\n",
                  "backend/composer.json": json.dumps({"require": {"php": "^8.2"}}),
                  "backend/public/index.php": "<?php echo 'api';\n",
                  "mobile/pubspec.yaml": "name: mobile\ndependencies:\n  flutter:\n    sdk: flutter\n",
                  "mobile/lib/main.dart": "void main() {}\n",
                  "site/index.html": "<h1>landing</h1>\n"},
}

SAMPLE_COPIES = {
    "S_LaravelBlog": SAMPLES / "Tests/Web/Laravel_Blog",
    "S_CodeIgniterShop": SAMPLES / "Tests/Web/CodeIgniter_Shop",
    "S_DjangoBlog": SAMPLES / "Tests/Web/Django_Blog",
    "S_FlaskTodo": SAMPLES / "Tests/Web/Flask_Todo",
    "S_FastAPIItems": SAMPLES / "Tests/Web/FastAPI_Items",
    "S_ExpressSite": SAMPLES / "Tests/Web/ExpressSite_Node",
    "S_NestJS": SAMPLES / "Tests/Web/NestJS_App",
    "S_ReactVite": SAMPLES / "Tests/Web/Frontend_React_Vite",
    "S_ShopSitePhp": SAMPLES / "Tests/Web/ShopSite_PhpSqlite",
    "S_StaticBootstrap": SAMPLES / "Tests/Web/StaticBootstrapSite",
    "S_AspNet": SAMPLES / "Tests/Web/AspNet_App",
    "S_HelloCSharp": SAMPLES / "HelloCSharp",
    "S_HelloPython": SAMPLES / "HelloPython",
    "S_VB6Calculator": SAMPLES / "Tests/ForeignProjects/VB6Calculator",
    "S_CMakeHello": SAMPLES / "Tests/ForeignProjects/CMakeHello",
    "S_DelphiConsole": SAMPLES / "Tests/ForeignProjects/DelphiConsole",
    "S_VsSolution": SAMPLES / "Tests/ForeignProjects/VsSolution",
}
IGN = shutil.ignore_patterns("node_modules", "vendor", ".venv", "venv", "bin", "obj", "_build", "target",
                             "__pycache__", "*.radsln", "project.radproj", ".radide", "dist", "build")


def main():
    CASES.mkdir(parents=True, exist_ok=True)
    only = set(sys.argv[1:])
    for name, files in HAND.items():
        if only and name not in only:
            continue
        fresh(name)
        for rel, text in files.items():
            w(f"{name}/{rel}", text)
    for name, src in SAMPLE_COPIES.items():
        if only and name not in only:
            continue
        d = fresh(name)
        shutil.copytree(src, d, ignore=IGN)
    print("cases:", len(list(CASES.iterdir())))


if __name__ == "__main__":
    main()
