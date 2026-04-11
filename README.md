# slides-capture

Tool to automate capture of slides for personal copy.

DO NOT USE ON COPYRIGHTED CONTENT


## Install

You can install directly from python (recommended for command line use) with
```
pip install -r requirements.txt
```

or you can install with docker (recommended for web use) with
```
docker compose up
```

Or via pyinstaller
```
venv\Scripts\activate
pip install pyinstaller
pyinstaller --add-data "config.json:." --add-data "icon.png:." --icon icon.png --windowed --onefile .\pdf-capture.py
```


## Use

From command line 
```
python pdf-capture.py --help
```

From web, open [http://localhost:5000](http://localhost:5000)


# Notes

- Use of headless mode will open a bundled headless chromium, non headless use your local chrome (useful if cookies needed)
- You will need to add some definitions of CSS selectors

See begining of file for configuration instructions and examples