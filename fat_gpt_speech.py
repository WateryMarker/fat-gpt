"""Male Thai speech via Edge TTS; pitch and speaking speed are independent."""
import queue
import re
import subprocess
import sys
import tempfile
import threading
from pathlib import Path


class SpeechPlayer:
    def __init__(self):
        self.errors = queue.Queue()
        self.lock = threading.Lock()
        self.generation = 0
        self.process = None
        self.closed = False
        self.voice = 'th-TH-NiwatNeural'
        self.tts_python = Path(__file__).resolve().parent / '.venv' / 'bin' / 'python'

    def stop(self):
        with self.lock:
            self.generation += 1
            process = self.process
            if process is not None and process.poll() is None:
                try:
                    process.terminate()
                except ProcessLookupError:
                    pass

    def close(self):
        with self.lock:
            self.closed = True
        self.stop()

    def speak(self, text, rate=5, pitch=-28):
        if sys.platform != 'darwin':
            self.errors.put('เสียงพูดนี้ใช้ได้บน macOS')
            return
        # Strip speech-engine commands and markup from model output.
        text = re.sub(r'\[\[.*?\]\]', '', text, flags=re.S)
        text = re.sub(r'https?://\S+', '', text)
        text = text.replace('*', '').replace('#', '').replace('`', '').strip()[:1600]
        if not text:
            return
        self.stop()
        with self.lock:
            if self.closed:
                return
            generation = self.generation
        threading.Thread(target=self._speak, args=(text, rate, pitch, generation), daemon=True).start()

    def _run(self, args, generation, text=None):
        with self.lock:
            if self.closed or generation != self.generation:
                return False
            process = subprocess.Popen(args, stdin=subprocess.PIPE if text is not None else subprocess.DEVNULL,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            self.process = process
        try:
            _, error = process.communicate(input=text.encode('utf-8') if text is not None else None, timeout=90)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise RuntimeError('สร้างเสียงนานเกินไป ลองข้อความสั้นลง')
        finally:
            with self.lock:
                if self.process is process:
                    self.process = None
        with self.lock:
            if self.closed or generation != self.generation:
                return False
        if process.returncode:
            raise RuntimeError(error.decode('utf-8', errors='replace').strip()[:200] or 'เล่นเสียงไม่สำเร็จ')
        return True

    def _speak(self, text, rate, pitch, generation):
        try:
            with tempfile.TemporaryDirectory(prefix='fat-gpt-voice-') as folder:
                text_file = Path(folder) / 'reply.txt'
                output = Path(folder) / 'niwat.mp3'
                text_file.write_text(text, encoding='utf-8')
                if not self.tts_python.exists():
                    raise RuntimeError('ยังไม่ได้ติดตั้งเสียงผู้ชาย ดูขั้นตอนติดตั้งใน README.md')
                # The service controls pitch independently; audio playback stays at 1x.
                if not self._run([str(self.tts_python), '-m', 'edge_tts', '--voice', self.voice,
                                  f'--rate={int(rate):+d}%', f'--pitch={int(pitch):+d}Hz',
                                  '--file', str(text_file), '--write-media', str(output)], generation):
                    return
                if not output.exists() or output.stat().st_size == 0:
                    raise RuntimeError('บริการเสียงไม่ส่งไฟล์กลับมา ลองใหม่อีกครั้ง')
                self._run(['afplay', str(output)], generation)
        except Exception as error:
            with self.lock:
                current = not self.closed and generation == self.generation
            if current:
                self.errors.put('สร้างเสียงผู้ชายไม่สำเร็จ เช็กอินเทอร์เน็ตหรือลองใหม่: ' + str(error)[-240:])
