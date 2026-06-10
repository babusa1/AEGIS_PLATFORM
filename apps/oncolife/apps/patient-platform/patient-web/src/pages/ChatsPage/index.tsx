// Export the new Symptom Checker Chat Page (rule-based)
import SymptomChatPage from './SymptomChatPage';

// Keep the old LLM-based ChatsPage available for reference
export { default as LegacyChatsPage } from './ChatsPage';

// Default export is now the Symptom Checker
export default SymptomChatPage;