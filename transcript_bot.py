import soundcard as sc
import numpy as np
import whisper
import threading
import time
import queue
import json
from datetime import datetime
import psutil
import os

class AudioTranscriptionBot:
    def __init__(self):
        print("🔧 Inicializando Teams Transcript Bot...")
        print("=" * 50)
        
        # Configuración
        self.sample_rate = 48000
        self.chunk_duration = 3  # segundos
        self.is_recording = False
        self.audio_queue = queue.Queue()
        self.transcriptions = []
        
        # Cargar modelo Whisper
        self.load_whisper_model()
        
        # Configurar audio
        self.setup_audio()
        
    def load_whisper_model(self):
        """Cargar modelo Whisper"""
        try:
            print("📥 Cargando modelo Whisper (puede tomar unos minutos la primera vez)...")
            self.whisper_model = whisper.load_model("base")
            print("✅ Modelo Whisper cargado exitosamente")
        except Exception as e:
            print(f"❌ Error cargando Whisper: {e}")
            raise
        
    def setup_audio(self):
        """Configurar captura de audio del sistema"""
        try:
            # Obtener dispositivo de salida por defecto (altavoces)
            self.default_speaker = sc.default_speaker()
            print(f"🔊 Dispositivo de audio detectado: {self.default_speaker.name}")
            
            # Configurar grabador con loopback para capturar lo que sale por altavoces
            self.recorder = self.default_speaker.recorder(
                samplerate=self.sample_rate,
                channels=1  # Mono es suficiente para voz
            )
            print("✅ Audio configurado correctamente")
            
        except Exception as e:
            print(f"❌ Error configurando audio: {e}")
            print("💡 Asegúrate de que el audio esté funcionando en tu sistema")
            
    def detect_teams_process(self):
        """Detectar si Microsoft Teams está ejecutándose"""
        teams_processes = ['teams.exe', 'ms-teams.exe', 'Teams.exe']
        
        for process in psutil.process_iter(['pid', 'name']):
            try:
                process_name = process.info['name']
                if any(teams_proc.lower() in process_name.lower() for teams_proc in teams_processes):
                    print(f"✅ Microsoft Teams detectado: {process_name}")
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return False
    
    def capture_audio_chunk(self):
        """Capturar chunk de audio del sistema"""
        try:
            # Grabar por la duración especificada
            audio_data = self.recorder.record(
                numframes=self.sample_rate * self.chunk_duration
            )
            
            # Convertir a numpy array
            audio_array = np.array(audio_data).flatten()
            
            # Verificar que no sea solo silencio
            audio_level = np.max(np.abs(audio_array))
            if audio_level > 0.005:  # Umbral de detección de audio
                print(f"🎵 Audio capturado (nivel: {audio_level:.3f})")
                return audio_array
            
        except Exception as e:
            print(f"❌ Error capturando audio: {e}")
            
        return None
    
    def transcribe_audio(self, audio_data):
        """Transcribir audio usando Whisper"""
        try:
            # Normalizar audio para Whisper
            audio_normalized = audio_data.astype(np.float32)
            
            # Transcribir con Whisper
            result = self.whisper_model.transcribe(
                audio_normalized,
                language="es",  # Español
                fp16=False,     # Usar float32 para compatibilidad
                verbose=False   # No mostrar logs internos
            )
            
            text = result["text"].strip()
            
            # Filtrar transcripciones muy cortas o sin contenido
            if len(text) > 5 and not text.lower() in ['gracias', 'muchas gracias', '']:
                return text
                
        except Exception as e:
            print(f"❌ Error en transcripción: {e}")
            
        return None
    
    def audio_capture_worker(self):
        """Worker thread para captura continua de audio"""
        print("🎤 Iniciando captura de audio...")
        
        while self.is_recording:
            try:
                # Capturar chunk de audio
                audio_chunk = self.capture_audio_chunk()
                
                if audio_chunk is not None:
                    # Enviar a cola de transcripción
                    self.audio_queue.put(audio_chunk)
                
                # Pequeña pausa para no saturar CPU
                time.sleep(0.5)
                
            except Exception as e:
                print(f"❌ Error en captura: {e}")
                time.sleep(1)
    
    def transcription_worker(self):
        """Worker thread para transcripción continua"""
        print("🔤 Iniciando motor de transcripción...")
        
        while self.is_recording or not self.audio_queue.empty():
            try:
                # Obtener audio de la cola
                audio_data = self.audio_queue.get(timeout=2)
                
                # Transcribir
                transcript = self.transcribe_audio(audio_data)
                
                if transcript:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    
                    # Almacenar transcripción
                    entry = {
                        "timestamp": timestamp,
                        "text": transcript
                    }
                    self.transcriptions.append(entry)
                    
                    # Mostrar en consola
                    print(f"📝 [{timestamp}] {transcript}")
                
                # Marcar tarea como completada
                self.audio_queue.task_done()
                
            except queue.Empty:
                # Timeout normal, continuar
                continue
            except Exception as e:
                print(f"❌ Error en transcripción: {e}")
    
    def start_recording(self):
        """Iniciar grabación y transcripción"""
        if self.is_recording:
            print("⚠️ La grabación ya está activa")
            return
            
        print("\n🎯 Verificando sistema...")
        
        # Verificar Teams (opcional)
        if self.detect_teams_process():
            print("✅ Microsoft Teams está ejecutándose")
        else:
            print("⚠️ Microsoft Teams no detectado")
            print("💡 El bot funcionará de todas formas capturando todo el audio del sistema")
        
        # Iniciar grabación
        print("\n🚀 Iniciando captura y transcripción...")
        self.is_recording = True
        self.transcriptions = []
        
        # Crear y iniciar threads
        self.audio_thread = threading.Thread(
            target=self.audio_capture_worker, 
            daemon=True,
            name="AudioCapture"
        )
        self.transcription_thread = threading.Thread(
            target=self.transcription_worker, 
            daemon=True,
            name="Transcription"
        )
        
        self.audio_thread.start()
        self.transcription_thread.start()
        
        print("✅ ¡Sistema activo! Las transcripciones aparecerán aquí:")
        print("-" * 50)
        print("💡 Presiona ENTER para detener la grabación")
    
    def stop_recording(self):
        """Detener grabación y transcripción"""
        if not self.is_recording:
            print("⚠️ No hay grabación activa")
            return
            
        print("\n⏹️ Deteniendo grabación...")
        self.is_recording = False
        
        # Esperar que terminen los threads
        print("🔄 Procesando últimas transcripciones...")
        if hasattr(self, 'audio_thread') and self.audio_thread.is_alive():
            self.audio_thread.join(timeout=5)
        if hasattr(self, 'transcription_thread') and self.transcription_thread.is_alive():
            self.transcription_thread.join(timeout=10)
            
        print("✅ Grabación detenida")
    
    def save_transcription(self, filename=None):
        """Guardar transcripción completa en archivos"""
        if not self.transcriptions:
            print("⚠️ No hay transcripciones para guardar")
            return None
            
        # Generar nombre de archivo si no se proporciona
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"transcripcion_teams_{timestamp}"
        
        # Guardar como JSON (datos estructurados)
        json_file = f"{filename}.json"
        try:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(self.transcriptions, f, ensure_ascii=False, indent=2)
            print(f"💾 Transcripción JSON guardada: {json_file}")
        except Exception as e:
            print(f"❌ Error guardando JSON: {e}")
        
        # Guardar como texto plano (fácil de leer)
        txt_file = f"{filename}.txt"
        try:
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write("TRANSCRIPCIÓN DE REUNIÓN\n")
                f.write("=" * 30 + "\n")
                f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total de entradas: {len(self.transcriptions)}\n\n")
                
                for entry in self.transcriptions:
                    f.write(f"[{entry['timestamp']}] {entry['text']}\n")
                    
            print(f"📄 Transcripción TXT guardada: {txt_file}")
        except Exception as e:
            print(f"❌ Error guardando TXT: {e}")
        
        return json_file, txt_file
    
    def get_full_transcript_text(self):
        """Obtener transcripción completa como texto único"""
        if not self.transcriptions:
            return ""
        
        return " ".join([entry['text'] for entry in self.transcriptions])
    
    def show_summary(self):
        """Mostrar resumen de la sesión"""
        print("\n" + "=" * 50)
        print("📊 RESUMEN DE LA SESIÓN")
        print("=" * 50)
        print(f"📝 Total de transcripciones: {len(self.transcriptions)}")
        
        if self.transcriptions:
            # Calcular duración aproximada
            if len(self.transcriptions) > 1:
                start_time = datetime.strptime(self.transcriptions[0]['timestamp'], "%H:%M:%S")
                end_time = datetime.strptime(self.transcriptions[-1]['timestamp'], "%H:%M:%S")
                duration = end_time - start_time
                print(f"⏱️ Duración aproximada: {duration}")
            
            # Mostrar primeras y últimas transcripciones
            print(f"\n📋 Primera transcripción:")
            print(f"   [{self.transcriptions[0]['timestamp']}] {self.transcriptions[0]['text']}")
            
            if len(self.transcriptions) > 1:
                print(f"\n📋 Última transcripción:")
                print(f"   [{self.transcriptions[-1]['timestamp']}] {self.transcriptions[-1]['text']}")
        
        print("=" * 50)

def main():
    """Función principal"""
    print("🤖 TEAMS AUDIO TRANSCRIPTION BOT")
    print("=" * 50)
    print("📋 Este bot captura el audio de tu sistema y lo transcribe en tiempo real")
    print("🎯 Ideal para reuniones de Teams, Zoom, Meet, etc.")
    print("💡 Asegúrate de tener audio funcionando antes de comenzar")
    print("=" * 50)
    
    # Crear instancia del bot
    try:
        bot = AudioTranscriptionBot()
    except Exception as e:
        print(f"❌ Error inicializando el bot: {e}")
        print("💡 Verifica que tengas audio funcionando y permisos adecuados")
        input("Presiona ENTER para salir...")
        return
    
    try:
        # Iniciar grabación
        bot.start_recording()
        
        # Esperar a que el usuario presione ENTER
        input()
        
        # Detener grabación
        bot.stop_recording()
        
        # Mostrar resumen
        bot.show_summary()
        
        # Guardar transcripción
        if bot.transcriptions:
            print("\n💾 Guardando transcripción...")
            files = bot.save_transcription()
            
            if files:
                print(f"\n✅ Archivos guardados exitosamente")
                print("🎉 ¡Transcripción completada!")
        else:
            print("⚠️ No se capturó audio para transcribir")
            print("💡 Verifica que haya audio reproduciéndose en tu sistema")
                
    except KeyboardInterrupt:
        print("\n\n👋 Interrumpido por el usuario")
        bot.stop_recording()
    except Exception as e:
        print(f"\n❌ Error durante la ejecución: {e}")
        bot.stop_recording()
    
    print("\n🔚 Aplicación finalizada")
    input("Presiona ENTER para cerrar...")

if __name__ == "__main__":
    main()
