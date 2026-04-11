


from src.capture import capture_pages_to_pdf
from src.config import DEFAULT_URL


tpl_html_main = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Capture Slides to PDF</title>
    <style>
        body { font-family: Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #333; margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; height: 100vh; }
        .container { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); max-width: 500px; width: 100%; }
        h1 { text-align: center; color: #4a5568; margin-bottom: 30px; }
        form { display: flex; flex-direction: column; }
        label { margin-bottom: 5px; font-weight: bold; color: #2d3748; }
        input[type="text"], input[type="number"] { padding: 10px; margin-bottom: 20px; border: 1px solid #e2e8f0; border-radius: 5px; font-size: 16px; width: 100%; box-sizing: border-box; }
        input[type="checkbox"] { margin-right: 10px; }
        .checkbox-label { display: flex; align-items: center; margin-bottom: 20px; }
        button { background: #667eea; color: white; padding: 12px; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; transition: background 0.3s; }
        button:hover { background: #5a67d8; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Capture Slides to PDF</h1>
        <form method="post" action="/process">
            <label for="url">URL du slideshow:</label>
            <input type="text" id="url" name="url" value="{{ url }}" required>
            
            <details style="margin-top: 20px;">
                <summary style="cursor: pointer; margin-bottom: 20px; font-weight: bold; color: #667eea;">Options avancées</summary>
                <div style="padding-top: 10px; border-top: 1px solid #e2e8f0; margin-top: 10px;">
                    <div style="margin-bottom: 20px;">
                        <label for="output">Nom du fichier PDF (optionnel, utilise le titre si vide):</label>
                        <input type="text" id="output" name="output" placeholder="Laisser vide pour utiliser le titre">
                    </div>
                    
                    <div style="margin-bottom: 20px;">
                        <label for="max_pages">Nombre max de pages (optionnel):</label>
                        <input type="number" id="max_pages" name="max_pages" min="1">
                    </div>
                    
                    <div>
                        <label class="checkbox-label">
                            <input type="checkbox" name="headless">
                            Mode headless (sans interface)
                        </label>
                    </div>
                </div>
            </details>
            
            <button type="submit">Démarrer la capture</button>
        </form>
    </div>
</body>
</html>
'''

tpl_html_process = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Traitement en cours</title>
    <style>
        body { font-family: Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #333; margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; height: 100vh; }
        .container { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); max-width: 600px; width: 100%; text-align: center; }
        h1 { color: #4a5568; margin-bottom: 30px; }
        #status { background: #f7fafc; padding: 15px; border-radius: 5px; margin-bottom: 20px; font-family: monospace; white-space: pre-wrap; min-height: 60px; display: flex; align-items: center; justify-content: center; }
        .progress-container { position: relative; width: 100%; height: 3em; background: #ddd; border-radius: 5px; overflow: hidden; }
        .progress-bar { height: 100%; background: green; position: relative; transition: width 0.3s; }
        .progress-bar.error { background: red; }
        .progress-label { position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 14px; }
        .download-btn { background: green; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Processing...</h1>
        <div id="title" style="margin-bottom: 10px; font-size: 18px; font-weight: bold;"></div>
        <div class="progress-container">
            <div class="progress-bar ok" id="progress-bar"></div>
            <div class="progress-label" id="progress-text">Initialization</div>
        </div>
        <div id="download-section" style="display: none; margin-top: 20px;">
            <a id="download-link" href="#" class="download-btn">Download PDF</a>
        </div>
        <img id="screenshot" style="display: block; margin: 20px auto; max-width: 100%; border: 1px solid #ccc;">
        <script>
            function update() {
                fetch('/progress').then(r => r.json()).then(data => {
                    if (data.title) {
                        document.getElementById('title').textContent = data.title;
                    }
                    document.getElementById('progress-bar').style.width = data.percent + '%';
                    document.getElementById('progress-bar').className = 'progress-bar ' + (data.status && (data.status.includes('Failed') || data.status.includes('Error')) ? 'error' : 'ok');
                    document.getElementById('progress-text').textContent = data.status || 'Initialisation';
                    if (data.file) {
                        document.getElementById('download-section').style.display = 'block';
                        document.getElementById('download-link').href = '/download/' + data.download_hash;
                        document.getElementById('screenshot').style.display = 'none';
                    }
                    if (data.screenshot_data) {
                        const img = document.getElementById('screenshot');
                        img.style.display = 'block';
                        img.src = data.screenshot_data;
                    }
                }).catch(err => console.error('Erreur de mise à jour:', err));
            }
            update();
            setInterval(update, 1000);
        </script>
    </div>
</body>
</html>
'''



def run_web_app(config):
    # Web application definition
    from flask import Flask, request, jsonify, render_template_string
    import threading

    app = Flask(__name__)
    progress = {'percent': 0, 'status': '', 'file': None, 'screenshot_data': None}
    download_hashes = {}

    def run_script(config):
        progress['screenshot_data'] = None
        capture_pages_to_pdf(config, progress, download_hashes)

    @app.route('/')
    def index():
        return render_template_string(tpl_html_main, url=config['url'] or DEFAULT_URL)
    
    @app.route('/process', methods=['POST'])
    def process():
        config['url'] = request.form['url']
        config['output'] = request.form['output'] if request.form['output'].strip() else None
        if config['output']:
            import os
            config['output'] = os.path.basename(config['output'])
            if not config['output'].endswith('.pdf'):
                config['output'] += '.pdf'
        if request.form.get('max_pages'):
            config['max_pages'] = int(request.form.get('max_pages', 0))
        config['headless'] = 'headless' in request.form
        threading.Thread(target=run_script, args=([config])).start()
        return render_template_string(tpl_html_process)   

    @app.route('/progress')
    def get_progress():
        return jsonify(progress)

    @app.route('/download/<hash>')
    def download(hash):
        import os
        from flask import send_file
        if hash in download_hashes:
            filename = download_hashes[hash]
            return send_file(os.path.join(config['output_path'], filename), as_attachment=True)
        return "File not found", 404

    app.run(host=config['host'], port=config['port'],debug=True, use_reloader=False)

