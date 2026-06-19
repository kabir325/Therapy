import json
import os
from datetime import datetime
from typing import List, Dict, Any
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

class AITherapist:
    def __init__(self, api_key: str = None):
        """Initialize the AI Therapist with OpenAI API"""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY environment variable or pass api_key parameter.")
        
        self.conversation_history: List[ConversationEntry] = []
        self.session_start_time = datetime.now()
        self.user_name = None
        self.emotional_patterns = {}
        
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

Remember:
- You are NOT providing medical advice or diagnosis
- Encourage professional help for serious mental health concerns
- Focus on being a supportive, listening presence
- Help clients explore their thoughts and feelings
- Guide them toward their own insights and solutions

Respond as Dr. Sarah would - with warmth, professionalism, and genuine care for the person you're speaking with."""

    def detect_emotional_state(self, message: str) -> str:
        """Analyze the emotional state from user's message"""
        emotional_indicators = {
            'anxious': ['worried', 'nervous', 'anxious', 'scared', 'panic', 'stress'],
            'depressed': ['sad', 'hopeless', 'empty', 'worthless', 'tired', 'exhausted'],
            'angry': ['angry', 'furious', 'frustrated', 'irritated', 'mad', 'rage'],
            'confused': ['confused', 'lost', 'uncertain', 'don\'t know', 'unclear'],
            'excited': ['excited', 'happy', 'thrilled', 'amazing', 'wonderful'],
            'calm': ['peaceful', 'relaxed', 'calm', 'content', 'okay', 'fine']
        }
        
        message_lower = message.lower()
        detected_emotions = []
        
        for emotion, indicators in emotional_indicators.items():
            if any(indicator in message_lower for indicator in indicators):
                detected_emotions.append(emotion)
        
        return detected_emotions[0] if detected_emotions else 'neutral'
    def generate_therapeutic_response(self, user_message: str, emotional_state: str) -e str:
        """Generate a therapeutic response using Ollama"""
        context = ""
        if self.conversation_history:
            recent_context = self.conversation_history[-3:]
            context = "Recent conversation context:\n"
            for entry in recent_context:
                context += f"Client: {entry.user_message}\n"
                context += f"Therapist: {entry.therapist_response}\n\n"

        prompt = f"{self.system_prompt}\n\n{context}"

        if emotional_state != 'neutral':
            prompt += f"\nThe client seems to be feeling {emotional_state}. Please respond with empathy.\n\n"

        prompt += f"Client: {user_message}\n\nDr. Sarah:"

        try:
            result = subprocess.run(
                ['ollama', 'generate', 'tinyllama:latest', '--prompt', prompt],
                capture_output=True, text=True
            )
            return result.stdout.strip()

        except Exception as e:
            return f"I'm having a moment of technical difficulty, but I'm still here with you. Can you tell me more about what's on your mind? (Error: {str(e)})"
            return f"I'm having a moment of technical difficulty, but I'm still here with you. Can you tell me a bit more about what's on your mind? (Error: {str(e)})"

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
        
        total_delay = min(reading_time + thinking_time + typing_time, 8)  # Cap at 8 seconds
        
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
        
        return response

    def extract_themes(self, message: str) -> str:
        """Extract key themes from user message"""
        themes = []
        theme_keywords = {
            'relationships': ['relationship', 'partner', 'friend', 'family', 'love'],
            'work': ['work', 'job', 'career', 'boss', 'colleague'],
            'anxiety': ['worry', 'anxious', 'nervous', 'panic', 'stress'],
            'depression': ['sad', 'hopeless', 'empty', 'tired', 'depressed'],
            'self_esteem': ['confidence', 'self-worth', 'insecure', 'doubt'],
            'change': ['change', 'transition', 'new', 'different', 'moving']
        }
        
        message_lower = message.lower()
        for theme, keywords in theme_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                themes.append(theme)
        
        return ', '.join(themes) if themes else 'general conversation'

    def save_session(self, filename: str = None):
        """Save conversation history to file"""
        if not filename:
            filename = filename or f"therapy_session_{self.user_name}.json"
        
        session_data = {
            'session_start': self.session_start_time.isoformat(),
            'session_end': datetime.now().isoformat(),
            'user_name': self.user_name,
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
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        print(f"Session saved to {filename}")

    def start_session(self):
        """Start an interactive therapy session"""
        print("\n" + "="*60)
        print("Welcome to Your AI Therapy Session")
        print("="*60)
        print("\nHi, I'm Dr. Sarah. I'm here to listen and support you.")
        print("Take your time, and share whatever feels comfortable for you.")
        print("\nType 'quit' to end the session, or 'save' to save progress.")
        print("-"*60)
        
        # Get user's name
        name_input = input("\nWhat would you like me to call you? ")
        self.user_name = name_input if name_input.strip() else "there"
        
        initial_greeting = f"Nice to meet you, {self.user_name}. How are you feeling today?"
        print(f"\nDr. Sarah: {initial_greeting}")
        
        # Main conversation loop
        while True:
            try:
                user_input = input(f"\n{self.user_name}: ").strip()
                
                if user_input.lower() == 'quit':
                    print(f"\nDr. Sarah: Thank you for sharing with me today, {self.user_name}. Take care of yourself.")
                    break
                elif user_input.lower() == 'save':
                    self.save_session()
                    continue
                elif not user_input:
                    print("Dr. Sarah: I'm here when you're ready to share.")
                    continue
                
                response = self.respond_to_user(user_input)
                print(f"\nDr. Sarah: {response}")
                
            except KeyboardInterrupt:
                print(f"\n\nDr. Sarah: I understand you need to go. Take care, {self.user_name}.")
                break
            except Exception as e:
                print(f"\nDr. Sarah: I'm experiencing some technical difficulties, but I'm still here with you. Error: {str(e)}")

if __name__ == "__main__":
    # Example usage
    try:
        # You'll need to set your OpenAI API key
        therapist = AITherapist()
        therapist.start_session()
    except ValueError as e:
        print(f"Error: {e}")
        print("Please set your OpenAI API key as an environment variable: OPENAI_API_KEY")
