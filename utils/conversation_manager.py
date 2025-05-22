import os
import json
import logging
from datetime import datetime

from config.settings import CONVERSATION_CACHE_DIR

# Configure logging
logger = logging.getLogger(__name__)

class ConversationManager:
    """
    Class to manage conversation threads and history.
    """
    
    def __init__(self):
        """
        Initialize the conversation manager.
        """
        self.active_threads = {}
        self.provided_information = {}  # Track provided information by thread
        self.load_all_conversations()
    def load_all_conversations(self):
        """
        Load all saved conversation histories.
        """
        try:
            # Get all conversation history files
            files = os.listdir(CONVERSATION_CACHE_DIR)
            
            for file in files:
                if file.endswith('.json'):
                    thread_id = file.split('.')[0]
                    file_path = os.path.join(CONVERSATION_CACHE_DIR, file)
                    
                    # Load the conversation history
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    
                    # Handle both old and new format
                    if isinstance(data, list):
                        # Old format (just a list of messages)
                        self.active_threads[thread_id] = data
                        self.provided_information[thread_id] = {}
                    elif isinstance(data, dict) and 'messages' in data:
                        # New format with metadata
                        self.active_threads[thread_id] = data['messages']
                        self.provided_information[thread_id] = data.get('metadata', {}).get('provided_information', {})
                    else:
                        # Unknown format, use as is
                        self.active_threads[thread_id] = data
                        self.provided_information[thread_id] = {}
                    
                    logger.info(f"Loaded conversation history for thread {thread_id}")
        
        except Exception as e:
            logger.error(f"Error loading conversation histories: {e}")
            import traceback
            logger.error(traceback.format_exc())
            logger.error(f"Error loading conversation histories: {e}")
    
    def get_conversation_history(self, thread_id):
        """
        Get the conversation history for a thread.
        
        Args:
            thread_id: ID of the email thread
        
        Returns:
            list: Conversation history
        """
        return self.active_threads.get(thread_id, [])
    def add_message(self, thread_id, role, content, provided_info=None):
        """
        Add a message to the conversation history.
        
        Args:
            thread_id: ID of the email thread
            role: Role of the message sender (applicant or system)
            content: Content of the message
            provided_info: Dictionary of provided information (optional)
        """
        try:
            # Initialize thread if it doesn't exist
            if thread_id not in self.active_threads:
                self.active_threads[thread_id] = []
            
            # Initialize provided information if it doesn't exist
            if thread_id not in self.provided_information:
                self.provided_information[thread_id] = {}
            
            # Create message object
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            }
            
            # Add provided information if available
            if provided_info and role == "applicant":
                message["provided_information"] = provided_info
                # Update the thread's provided information
                self.provided_information[thread_id].update(provided_info)
            
            # Add the message
            self.active_threads[thread_id].append(message)
            
            # Save the conversation history
            self.save_conversation(thread_id)
            
            logger.info(f"Added {role} message to thread {thread_id}")
        
        except Exception as e:
            logger.error(f"Error adding message to conversation: {e}")
            import traceback
            logger.error(traceback.format_exc())
            logger.error(f"Error adding message to conversation: {e}")
    
    def save_conversation(self, thread_id):
        """
        Save conversation history to a file.
        
        Args:
            thread_id: ID of the email thread
        """
        try:
            if thread_id in self.active_threads:
                # Create the file path
                file_path = os.path.join(CONVERSATION_CACHE_DIR, f"{thread_id}.json")
                
                # Create a copy of the conversation history
                conversation_data = self.active_threads[thread_id]
                
                # Add metadata with provided information
                conversation_data_with_metadata = {
                    "messages": conversation_data,
                    "metadata": {
                        "provided_information": self.provided_information.get(thread_id, {})
                    }
                }
                
                # Save the conversation history with metadata
                with open(file_path, 'w') as f:
                    json.dump(conversation_data_with_metadata, f, indent=2)
                
                logger.info(f"Saved conversation history for thread {thread_id}")
        
        except Exception as e:
            logger.error(f"Error saving conversation history: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def complete_conversation(self, thread_id):
        """
        Mark a conversation as complete and remove it from active threads.
        
        Args:
            thread_id: ID of the email thread
        """
        try:
            if thread_id in self.active_threads:
                # Save the conversation history one last time
                self.save_conversation(thread_id)
                
                # Remove from active threads
                del self.active_threads[thread_id]
                
                logger.info(f"Completed conversation for thread {thread_id}")
        
        except Exception as e:
            logger.error(f"Error completing conversation: {e}")
    
    def get_active_thread_count(self):
        """
        Get the number of active threads.
        
        Returns:
            int: Number of active threads
        """
        return len(self.active_threads)
    
    def get_thread_summary(self, thread_id):
        """
        Get a summary of a conversation thread.
        
        Args:
            thread_id: ID of the email thread
        
        Returns:
            dict: Thread summary
        """
        try:
            if thread_id in self.active_threads:
                history = self.active_threads[thread_id]
                
                # Get the first and last messages
                first_message = history[0] if history else None
                last_message = history[-1] if history else None
                
                # Count messages by role
                applicant_messages = sum(1 for msg in history if msg["role"] == "applicant")
                system_messages = sum(1 for msg in history if msg["role"] == "system")
                
                return {
                    "thread_id": thread_id,
                    "message_count": len(history),
                    "applicant_messages": applicant_messages,
                    "system_messages": system_messages,
                    "first_message_time": first_message.get("timestamp") if first_message else None,
                    "last_message_time": last_message.get("timestamp") if last_message else None,
                    "last_message_role": last_message.get("role") if last_message else None
                }
            
            return None
        
        except Exception as e:
            logger.error(f"Error getting thread summary: {e}")
            return None
    
    def get_all_thread_summaries(self):
        """
        Get summaries of all active threads.
        
        Returns:
            list: List of thread summaries
        """
        return [self.get_thread_summary(thread_id) for thread_id in self.active_threads]
    
    def update_provided_information(self, thread_id, provided_info):
        """
        Update the provided information for a thread.
        
        Args:
            thread_id: ID of the email thread
            provided_info: Dictionary of provided information
        """
        try:
            # Initialize provided information if it doesn't exist
            if thread_id not in self.provided_information:
                self.provided_information[thread_id] = {}
            
            # Update the provided information
            self.provided_information[thread_id].update(provided_info)
            
            # Save the conversation history
            self.save_conversation(thread_id)
            
            logger.info(f"Updated provided information for thread {thread_id}")
        
        except Exception as e:
            logger.error(f"Error updating provided information: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def get_provided_information(self, thread_id):
        """
        Get the provided information for a thread.
        
        Args:
            thread_id: ID of the email thread
        
        Returns:
            dict: Provided information
        """
        return self.provided_information.get(thread_id, {})