from quart import Quart, send_from_directory
import os

app = Quart(__name__, static_folder='public')

@app.route('/')
async def index():
    return await send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
async def static_files(path):
    return await send_from_directory(app.static_folder, path)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)