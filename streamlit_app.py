import streamlit as st
import asyncio
import threading
import os
import time
from pieces.torrent import Torrent
from pieces.client import TorrentClient

# Helper to run asyncio in a thread
class AsyncioThread(threading.Thread):
    def __init__(self, coro):
        super().__init__()
        self.coro = coro
        self.loop = asyncio.new_event_loop()
        self.exc = None

    def run(self):
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.coro)
        except Exception as e:
            self.exc = e
        finally:
            self.loop.close()

    def stop(self):
        for task in asyncio.all_tasks(self.loop):
            task.cancel()
        self.loop.call_soon_threadsafe(self.loop.stop)

# Streamlit UI
st.title('BitTorrent Client')

if 'client_thread' not in st.session_state:
    st.session_state.client_thread = None
if 'torrent_client' not in st.session_state:
    st.session_state.torrent_client = None
if 'torrent' not in st.session_state:
    st.session_state.torrent = None
if 'download_started' not in st.session_state:
    st.session_state.download_started = False
if 'progress' not in st.session_state:
    st.session_state.progress = 0
if 'status' not in st.session_state:
    st.session_state.status = ''

uploaded_file = st.file_uploader('Upload a .torrent file', type=['torrent'])

# Save uploaded file
torrent_path = None
if uploaded_file is not None:
    torrent_path = os.path.join('uploaded.torrent')
    with open(torrent_path, 'wb') as f:
        f.write(uploaded_file.read())
    st.session_state.torrent = Torrent(torrent_path)
    st.write('Torrent loaded:')
    st.write(str(st.session_state.torrent))

# Start download
if st.button('Start Download', disabled=st.session_state.download_started or st.session_state.torrent is None):
    st.session_state.torrent_client = TorrentClient(st.session_state.torrent)
    def run_client():
        async def download():
            await st.session_state.torrent_client.start()
        thread = AsyncioThread(download())
        st.session_state.client_thread = thread
        thread.start()
    run_client()
    st.session_state.download_started = True
    st.session_state.status = 'Download started.'

# Stop download
if st.button('Stop Download', disabled=not st.session_state.download_started):
    if st.session_state.torrent_client:
        st.session_state.torrent_client.stop()
    if st.session_state.client_thread:
        st.session_state.client_thread.stop()
    st.session_state.download_started = False
    st.session_state.status = 'Download stopped.'

# Progress and status
def get_progress():
    client = st.session_state.torrent_client
    if client is None:
        return 0, 0, 0
    pm = client.piece_manager
    if pm is None:
        return 0, 0, 0
    total = pm.total_pieces
    have = len(pm.have_pieces)
    percent = (have / total) * 100 if total else 0
    return have, total, percent

if st.session_state.download_started:
    have, total, percent = get_progress()
    st.progress(percent / 100)
    st.write(f"Downloaded {have} / {total} pieces ({percent:.2f}%)")
    st.session_state.status = f"Downloaded {have} / {total} pieces ({percent:.2f}%)"

st.write(st.session_state.status) 