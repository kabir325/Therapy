import json
import os
import glob
from datetime import datetime
from typing import List, Dict, Any, Optional
import subprocess
from dataclasses import dataclass
import time
import random

@dataclass
class ConversationEntry:
    timestamp: str
    user_message: str
    therapist_response: str
    emotional_state: str
    session_notes: str

class PrivateAITherapist:
    def __init__(self, model_name: str = "llama3.2:3b"):
        """Initialize the Private AI Therapist with Ollama"""
        self.model_name = model_name
        self.conversation_history: List[ConversationEntry] = []
        self.session_start_time = datetime.now()
        self.user_name = None
        self.session_file = None
        self.sessions_dir = "therapy_sessions"
        
        # Create sessions directory if it doesn't exist
        os.makedirs(self.sessions_dir, exist_ok=True)
        
        # Therapeutic techniques and responses
        self.therapeutic_techniques = {
            'active_listening': [
                "I hear you saying...",
                "It sounds like you're feeling...",
                "Help me understand...",
                "What I'm hearing is..."
            ],
            'reflection': [
                "How does that make you feel?",
                "What do you think about that?",
                "Can you tell me more about that experience?",
                "What comes up for you when you think about that?"
            ],
            'validation': [
                "That sounds really difficult.",
                "Your feelings are completely valid.",
                "It makes sense that you'd feel that way.",
                "Thank you for sharing something so personal."
            ],
            'cognitive_reframing': [
                "What evidence do you have for that thought?",
                "Is there another way to look at this situation?",
                "What would you tell a friend in this situation?",
                "How might this look different in a week or month?"
            ]
        }
        
        self.system_prompt = """You are Dr. Sarah, a warm, empathetic, and highly skilled therapist with 15 years of experience. Your goal is to create a safe, non-judgmental space where clients feel heard and understood.

Core principles:
- Always prioritize the client's emotional well-being
- Use active listening and validation techniques
- Ask thoughtful, open-ended questions
- Reflect back what you hear to show understanding
- Be genuinely curious about their experiences
- Maintain appropriate therapeutic boundaries
- Use evidence-based techniques (CBT, mindfulness, etc.)
- Show authentic empathy and warmth

Communication style:
- Speak naturally and conversationally, not clinically
- Use "I" statements to share observations gently
- Incorporate brief pauses in conversation (use "..." thoughtfully)
- Show emotional attunement through your responses
- Be present-focused but acknowledge past experiences
- Balance support with gentle challenges when appropriate
- Provide thoughtful, complete responses that fully address the client's needs

Remember:
- You are NOT providing medical advice or diagnosis
- Encourage professional help for serious mental health concerns
- Focus on being a supportive, listening presence
- Help clients explore their thoughts and feelings
- Guide them toward their own insights and solutions

Respond as Dr. Sarah would - with warmth, professionalism, and genuine care for the person you're speaking with."""

    def check_ollama_availability(self) -> bool:
        """Check if Ollama is running and model is available"""
        try:
            result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
            return self.model_name in result.stdout
        except:
            return False

    def detect_emotional_state(self, message: str) -> str:
        """Analyze the emotional state from user's message"""
        emotional_indicators = {
            'anxious': ['worried', 'nervous', 'anxious', 'scared', 'panic', 'stress', 'overwhelmed'],
            'depressed': ['sad', 'hopeless', 'empty', 'worthless', 'tired', 'exhausted', 'down'],
            'angry': ['angry', 'furious', 'frustrated', 'irritated', 'mad', 'rage', 'annoyed'],
            'confused': ['confused', 'lost', 'uncertain', 'don\'t know', 'unclear', 'mixed up'],
            'excited': ['excited', 'happy', 'thrilled', 'amazing', 'wonderful', 'great', 'fantastic'],
            'calm': ['peaceful', 'relaxed', 'calm', 'content', 'okay', 'fine', 'stable']
        }
        
        message_lower = message.lower()
        detected_emotions = []
        
        for emotion, indicators in emotional_indicators.items():
            if any(indicator in message_lower for indicator in indicators):
                detected_emotions.append(emotion)
        
        return detected_emotions[0] if detected_emotions else 'neutral'

    def generate_therapeutic_response(self, user_message: str, emotional_state: str) -> str:
        """Generate a therapeutic response using Ollama"""
        context = ""
        if self.conversation_history:
            recent_context = self.conversation_history[-3:]  # Last 3 exchanges
            context = "Previous conversation context:\\n"
            for entry in recent_context:
                context += f"Client: {entry.user_message}\\n"
                context += f"Dr. Sarah: {entry.therapist_response}\\n\\n"

        prompt = f"{self.system_prompt}\\n\\n{context}"

        if emotional_state != 'neutral':
            prompt += f"\\nThe client seems to be feeling {emotional_state}. Please respond with appropriate empathy and therapeutic techniques.\\n\\n"

        prompt += f"Client: {user_message}\\n\\nDr. Sarah:"

        try:
            result = subprocess.run(
                ['ollama', 'run', self.model_name],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=30,
                encoding='utf-8',
                errors='replace'
            )
            
            if result.returncode == 0:
                response = result.stdout.strip()
                # Clean up the response
                if response.startswith("Dr. Sarah:"):
                    response = response[10:].strip()
                
                # Remove any non-printable characters that might cause issues
                response = ''.join(char for char in response if char.isprintable() or char.isspace())
                
                return response if response else "I'm here with you. Can you tell me more about what you're experiencing?"
            else:
                return "I'm having a moment of technical difficulty, but I'm still here with you. Can you tell me more about what's on your mind?"
            
        except subprocess.TimeoutExpired:
            return "I'm taking a moment to think... Can you tell me more about what you're experiencing?"
        except UnicodeDecodeError:
            return "I'm having some technical difficulties with processing, but I'm still here with you. What's most important for you to share right now?"
        except Exception as e:
            return f"I'm experiencing some technical difficulties, but I'm still here with you. What's most important for you to share right now?"

    def add_human_touches(self, response: str) -> str:
        """Add human-like elements to the response"""
        # Add occasional thoughtful pauses
        if random.random() < 0.3:  # 30% chance
            pause_points = ['. ', '? ', ', ']
            for point in pause_points:
                if point in response:
                    response = response.replace(point, point + '... ', 1)
                    break
        
        # Add supportive interjections occasionally
        supportive_interjections = [
            "Mm-hmm, ",
            "I see, ",
            "Yes, ",
            "Right, "
        ]
        
        if random.random() < 0.2:  # 20% chance
            interjection = random.choice(supportive_interjections)
            response = interjection + response
        
        return response

    def simulate_typing_delay(self, text: str):
        """Simulate natural typing delay"""
        # Simulate reading time (humans read ~200 words per minute)
        word_count = len(text.split())
        reading_time = word_count / 200 * 60  # seconds
        
        # Simulate thinking time (1-3 seconds)
        thinking_time = random.uniform(1, 3)
        
        # Simulate typing time (humans type ~40 WPM)
        typing_time = word_count / 40 * 60  # seconds
        
        total_delay = min(reading_time + thinking_time + typing_time, 6)  # Cap at 6 seconds
        
        print("Dr. Sarah is typing...")
        time.sleep(total_delay)

    def respond_to_user(self, user_message: str) -> str:
        """Main method to respond to user input"""
        # Detect emotional state
        emotional_state = self.detect_emotional_state(user_message)
        
        # Simulate natural response time
        self.simulate_typing_delay(user_message)
        
        # Generate therapeutic response
        response = self.generate_therapeutic_response(user_message, emotional_state)
        
        # Add human touches
        response = self.add_human_touches(response)
        
        # Create session notes
        session_notes = f"Emotional state: {emotional_state}. Key themes: {self.extract_themes(user_message)}"
        
        # Save conversation entry
        entry = ConversationEntry(
            timestamp=datetime.now().isoformat(),
            user_message=user_message,
            therapist_response=response,
            emotional_state=emotional_state,
            session_notes=session_notes
        )
        self.conversation_history.append(entry)
        
        # Auto-save after each response
        self.save_session()
        
        return response

    def extract_themes(self, message: str) -> str:
        """Extract key themes from user message"""
        themes = []
        theme_keywords = {
            'relationships': ['relationship', 'partner', 'friend', 'family', 'love', 'dating'],
            'work': ['work', 'job', 'career', 'boss', 'colleague', 'workplace'],
            'anxiety': ['worry', 'anxious', 'nervous', 'panic', 'stress', 'overwhelmed'],
            'depression': ['sad', 'hopeless', 'empty', 'tired', 'depressed', 'down'],
            'self_esteem': ['confidence', 'self-worth', 'insecure', 'doubt', 'worthless'],
            'change': ['change', 'transition', 'new', 'different', 'moving', 'starting'],
            'health': ['health', 'sick', 'pain', 'medical', 'doctor', 'treatment'],
            'trauma': ['trauma', 'abuse', 'hurt', 'painful', 'difficult', 'hard']
        }
        
        message_lower = message.lower()
        for theme, keywords in theme_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                themes.append(theme)
        
        return ', '.join(themes) if themes else 'general conversation'

    def save_session(self):
        """Save conversation history to file"""
        if not self.session_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.session_file = os.path.join(self.sessions_dir, f"session_{self.user_name}_{timestamp}.json")
        
        session_data = {
            'session_start': self.session_start_time.isoformat(),
            'session_end': datetime.now().isoformat(),
            'user_name': self.user_name,
            'model_used': self.model_name,
            'conversation_history': [
                {
                    'timestamp': entry.timestamp,
                    'user_message': entry.user_message,
                    'therapist_response': entry.therapist_response,
                    'emotional_state': entry.emotional_state,
                    'session_notes': entry.session_notes
                } for entry in self.conversation_history
            ]
        }
        
        with open(self.session_file, 'w', encoding='utf-8', errors='replace') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)

    def list_previous_sessions(self) -> List[Dict]:
        """List all previous therapy sessions"""
        sessions = []
        session_files = glob.glob(os.path.join(self.sessions_dir, "session_*.json"))
        
        for file_path in session_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    session_data = json.load(f)
                    sessions.append({
                        'file': file_path,
                        'user_name': session_data.get('user_name', 'Unknown'),
                        'session_start': session_data.get('session_start', ''),
                        'message_count': len(session_data.get('conversation_history', []))
                    })
            except Exception as e:
                print(f"Error reading session file {file_path}: {e}")
        
        return sorted(sessions, key=lambda x: x['session_start'], reverse=True)

    def load_session(self, session_file: str) -> bool:
        """Load a previous therapy session"""
        try:
            with open(session_file, 'r', encoding='utf-8', errors='replace') as f:
                session_data = json.load(f)
            
            self.user_name = session_data.get('user_name', 'there')
            self.session_start_time = datetime.fromisoformat(session_data.get('session_start', datetime.now().isoformat()))
            self.session_file = session_file
            
            # Load conversation history
            self.conversation_history = []
            for entry_data in session_data.get('conversation_history', []):
                entry = ConversationEntry(
                    timestamp=entry_data['timestamp'],
                    user_message=entry_data['user_message'],
                    therapist_response=entry_data['therapist_response'],
                    emotional_state=entry_data['emotional_state'],
                    session_notes=entry_data['session_notes']
                )
                self.conversation_history.append(entry)
            
            return True
        except Exception as e:
            print(f"Error loading session: {e}")
            return False

    def show_session_summary(self):
        """Show a summary of the current session"""
        if not self.conversation_history:
            print("No conversation history in current session.")
            return
        
        print(f"\\n--- Session Summary for {self.user_name} ---")
        print(f"Started: {self.session_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Messages exchanged: {len(self.conversation_history)}")
        
        # Show emotional patterns
        emotions = [entry.emotional_state for entry in self.conversation_history]
        emotion_counts = {}
        for emotion in emotions:
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        print("\\nEmotional patterns:")
        for emotion, count in sorted(emotion_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {emotion}: {count} times")
        
        # Show themes
        all_themes = []
        for entry in self.conversation_history:
            themes = entry.session_notes.split("Key themes: ")[1] if "Key themes: " in entry.session_notes else ""
            if themes and themes != "general conversation":
                all_themes.extend([theme.strip() for theme in themes.split(',')])
        
        if all_themes:
            theme_counts = {}
            for theme in all_themes:
                theme_counts[theme] = theme_counts.get(theme, 0) + 1
            
            print("\\nMain themes discussed:")
            for theme, count in sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"  {theme}: {count} times")

    def start_session(self):
        """Start an interactive therapy session"""
        if not self.check_ollama_availability():
            print(f"Error: Ollama is not running or model '{self.model_name}' is not available.")
            print("Please make sure Ollama is running and the model is installed.")
            return
        
        print("\\n" + "="*70)
        print("🧠 Private AI Therapy Session (Powered by Ollama)")
        print("="*70)
        print("\\nWelcome! This is a completely private therapy session.")
        print("All conversations are stored locally on your computer.")
        print("\\nAvailable commands:")
        print("  'quit' - End the session")
        print("  'save' - Manually save progress")
        print("  'history' - View previous sessions")
        print("  'summary' - Show current session summary")
        print("  'continue' - Continue a previous session")
        print("-"*70)
        
        # Check for existing sessions
        previous_sessions = self.list_previous_sessions()
        
        if previous_sessions:
            print(f"\\n📁 Found {len(previous_sessions)} previous sessions")
            continue_choice = input("Would you like to continue a previous session? (y/n): ").lower()
            
            if continue_choice == 'y':
                print("\\nPrevious sessions:")
                for i, session in enumerate(previous_sessions[:10], 1):  # Show last 10
                    start_time = datetime.fromisoformat(session['session_start']).strftime('%Y-%m-%d %H:%M')
                    print(f"  {i}. {session['user_name']} - {start_time} ({session['message_count']} messages)")
                
                try:
                    choice = int(input("\\nEnter session number to continue (0 for new session): "))
                    if 1 <= choice <= len(previous_sessions):
                        selected_session = previous_sessions[choice - 1]
                        if self.load_session(selected_session['file']):
                            print(f"\\n✅ Continued session with {self.user_name}")
                            print(f"📝 {len(self.conversation_history)} previous messages loaded")
                            
                            # Show last few messages for context
                            if self.conversation_history:
                                print("\\n--- Last conversation ---")
                                for entry in self.conversation_history[-2:]:
                                    print(f"{self.user_name}: {entry.user_message}")
                                    print(f"Dr. Sarah: {entry.therapist_response}\\n")
                        else:
                            print("❌ Failed to load session. Starting new session.")
                except ValueError:
                    print("Invalid choice. Starting new session.")
        
        # Get user's name if not loaded from session
        if not self.user_name:
            name_input = input("\\nWhat would you like me to call you? ")
            self.user_name = name_input.strip() if name_input.strip() else "there"
        
        print(f"\\nDr. Sarah: Nice to {'see you again' if self.conversation_history else 'meet you'}, {self.user_name}. How are you feeling today?")
        
        # Main conversation loop
        while True:
            try:
                user_input = input(f"\\n{self.user_name}: ").strip()
                
                if user_input.lower() == 'quit':
                    print(f"\\nDr. Sarah: Thank you for sharing with me today, {self.user_name}. Take care of yourself.")
                    print(f"💾 Session saved to: {self.session_file}")
                    break
                elif user_input.lower() == 'save':
                    self.save_session()
                    print(f"💾 Session saved to: {self.session_file}")
                    continue
                elif user_input.lower() == 'history':
                    sessions = self.list_previous_sessions()
                    print(f"\\n📁 Previous sessions ({len(sessions)} total):")
                    for i, session in enumerate(sessions[:10], 1):
                        start_time = datetime.fromisoformat(session['session_start']).strftime('%Y-%m-%d %H:%M')
                        print(f"  {i}. {session['user_name']} - {start_time} ({session['message_count']} messages)")
                    continue
                elif user_input.lower() == 'summary':
                    self.show_session_summary()
                    continue
                elif user_input.lower() == 'continue':
                    print("You're already in a session. Use 'quit' to end and start a new one.")
                    continue
                elif not user_input:
                    print("Dr. Sarah: I'm here when you're ready to share.")
                    continue
                
                response = self.respond_to_user(user_input)
                print(f"\\nDr. Sarah: {response}")
                
            except KeyboardInterrupt:
                print(f"\\n\\nDr. Sarah: I understand you need to go. Take care, {self.user_name}.")
                print(f"💾 Session saved to: {self.session_file}")
                break
            except Exception as e:
                print(f"\\nDr. Sarah: I'm experiencing some technical difficulties, but I'm still here with you.")
                print(f"Technical details: {str(e)}")

if __name__ == "__main__":
    therapist = PrivateAITherapist()
    therapist.start_session()
