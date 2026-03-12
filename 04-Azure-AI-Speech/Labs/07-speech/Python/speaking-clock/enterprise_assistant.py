import os
import time
import azure.cognitiveservices.speech as speech_sdk
from dotenv import load_dotenv

def main():
    load_dotenv()
    
    # Configuration
    speech_key = os.getenv('AI_SERVICE_KEY') or "7wuX8LKfmS10qDChHeTdE7CA0oV0LjRAPNFPRsZs67b0J4iK09BiJQQJ99CCACYeBjFXJ3w3AAAYACOGiNem"
    speech_region = "eastus"
    
    speech_config = speech_sdk.SpeechConfig(subscription=speech_key, region=speech_region)
    # Set premium neural voice
    speech_config.speech_synthesis_voice_name = "en-US-AvaNeural"
    
    audio_config = speech_sdk.AudioConfig(use_default_microphone=True)
    speech_recognizer = speech_sdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
    speech_synthesizer = speech_sdk.SpeechSynthesizer(speech_config=speech_config)

    print("\n--- Advanced Enterprise Assistant ---")
    print("Speak naturally. Say 'stop' or 'exit' to end the session.")
    print("System is listening continuously...")

    # For continuous recognition
    done = False

    def stop_cb(evt):
        print('CLOSING on {}'.format(evt))
        nonlocal done
        done = True

    def handle_recognized(evt):
        text = evt.result.text
        if text:
            print(f"\nUser: {text}")
            
            # Simple business logic for the demo
            if "status" in text.lower():
                response = "All enterprise systems are currently operational and within SLA limits."
            elif "billing" in text.lower():
                response = "Your current billing cycle ends in 5 days. No outstanding invoices found."
            elif "support" in text.lower():
                response = "I have initiated a high-priority support ticket for you. A representative will be with you shortly."
            elif any(exit_word in text.lower() for exit_word in ["stop", "exit", "quit"]):
                response = "Thank you for using the Enterprise Assistant. Goodbye!"
                nonlocal done
                done = True
            else:
                response = f"I'm sorry, I don't have enough information about '{text}'. Would you like me to connect you to a human agent?"

            print(f"Assistant: {response}")
            speech_synthesizer.speak_text_async(response).get()

    speech_recognizer.recognized.connect(handle_recognized)
    speech_recognizer.session_stopped.connect(stop_cb)
    speech_recognizer.canceled.connect(stop_cb)

    # Start continuous recognition
    speech_recognizer.start_continuous_recognition()
    
    try:
        while not done:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping...")
        speech_recognizer.stop_continuous_recognition()
    finally:
        speech_recognizer.stop_continuous_recognition()

if __name__ == "__main__":
    main()
