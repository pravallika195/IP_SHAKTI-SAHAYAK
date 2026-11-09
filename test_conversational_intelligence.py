"""Comprehensive Verification Suite for Conversational Intelligence in PatentAssistantEngine.
Tests:
1. GREETING variations: hi, hiii, hello, heyy, hellooo
2. TIME_GREETING variations: good morning, good afternoon, good evening
3. GRATITUDE variations: thanks, thank you, thx, thank you so much
4. ACKNOWLEDGEMENT variations: ok, okay, got it, alright, understood
5. IDENTITY inquiry: who are you?, what can you do?
6. FAREWELL variations: bye, goodbye, see you, take care
7. Multi-turn flow: Greeting followed by an AYUSH question
8. Multi-turn flow: AYUSH question followed by contextual follow-up with pronouns
9. Boundary safety: Research questions containing conversational words:
   - "high bioavailability curcumin formulations and piperine synergy" (contains 'high')
   - "is it ok to combine turmeric with piperine under patent claims?" (contains 'ok')
   - "thanks to curcumin's anti-inflammatory properties, what are its indications?" (contains 'thanks')
   - "what are the bye-products of solvent extraction of haridra rhizome?" (contains 'bye')
10. Safe classification failure & fallback:
    - Obvious conversational message falls back safely
    - Obvious research question falls back safely
    - Ambiguous / uncertain message falls back to CLARIFICATION (no irrelevant retrieval)
11. Zero ChromaDB retrieval for conversational categories (sources == [] and citation_audit is None)
12. Multilingual conversational synthesis (English, Hindi, Telugu)
"""
import sys
import unittest
from unittest.mock import patch, MagicMock

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from assistant_engine import PatentAssistantEngine, SUPPORTED_CATEGORIES, CONVERSATIONAL_CATEGORIES


class TestPatentAssistantConversationalIntelligence(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine = PatentAssistantEngine(top_k=4)

    def setUp(self):
        self.engine.reset_conversation()

    # --------------------------------------------------------------------------
    # 1. GREETINGS
    # --------------------------------------------------------------------------
    def test_greetings(self):
        queries = ["hi", "hii", "hiii", "hello", "heyy", "hellooo"]
        for q in queries:
            intent = self.engine.classify_intent(q)
            self.assertEqual(intent["category"], "GREETING", f"Failed for '{q}': got {intent['category']}")
            
            res = self.engine.ask(q)
            self.assertEqual(res["category"], "GREETING")
            self.assertEqual(len(res["sources"]), 0, f"Conversational query '{q}' should have 0 sources")
            self.assertIsNone(res["citation_audit"])
            self.assertTrue(len(res["answer"]) > 10)
            self.assertFalse("### Summary" in res["answer"], "Conversational greeting should not generate a RAG report")

    # --------------------------------------------------------------------------
    # 2. TIME GREETINGS
    # --------------------------------------------------------------------------
    def test_time_greetings(self):
        queries = ["good morning", "good afternoon", "good evening"]
        for q in queries:
            intent = self.engine.classify_intent(q)
            self.assertEqual(intent["category"], "TIME_GREETING", f"Failed for '{q}': got {intent['category']}")
            
            res = self.engine.ask(q)
            self.assertEqual(res["category"], "TIME_GREETING")
            self.assertEqual(len(res["sources"]), 0)
            self.assertIsNone(res["citation_audit"])
            # Ensure time-appropriate response
            if "morning" in q:
                self.assertIn("morning", res["answer"].lower())
            elif "afternoon" in q:
                self.assertIn("afternoon", res["answer"].lower())
            elif "evening" in q:
                self.assertIn("evening", res["answer"].lower())

    # --------------------------------------------------------------------------
    # 3. GRATITUDE
    # --------------------------------------------------------------------------
    def test_gratitude(self):
        queries = ["thanks", "thank you", "thx", "thank you so much"]
        for q in queries:
            intent = self.engine.classify_intent(q)
            self.assertEqual(intent["category"], "GRATITUDE", f"Failed for '{q}': got {intent['category']}")
            
            res = self.engine.ask(q)
            self.assertEqual(res["category"], "GRATITUDE")
            self.assertEqual(len(res["sources"]), 0)
            self.assertIsNone(res["citation_audit"])
            self.assertIn("welcome", res["answer"].lower())

    # --------------------------------------------------------------------------
    # 4. ACKNOWLEDGEMENT
    # --------------------------------------------------------------------------
    def test_acknowledgement(self):
        queries = ["ok", "okay", "got it", "alright", "understood"]
        for q in queries:
            intent = self.engine.classify_intent(q)
            self.assertEqual(intent["category"], "ACKNOWLEDGEMENT", f"Failed for '{q}': got {intent['category']}")
            
            res = self.engine.ask(q)
            self.assertEqual(res["category"], "ACKNOWLEDGEMENT")
            self.assertEqual(len(res["sources"]), 0)
            self.assertIsNone(res["citation_audit"])
            self.assertTrue(len(res["answer"]) < 200, "Acknowledgement should be concise, not a canned pitch")

    # --------------------------------------------------------------------------
    # 5. IDENTITY
    # --------------------------------------------------------------------------
    def test_identity(self):
        queries = ["who are you?", "who are you", "what can you do?", "what is your name"]
        for q in queries:
            intent = self.engine.classify_intent(q)
            self.assertEqual(intent["category"], "IDENTITY", f"Failed for '{q}': got {intent['category']}")
            
            res = self.engine.ask(q)
            self.assertEqual(res["category"], "IDENTITY")
            self.assertEqual(len(res["sources"]), 0)
            self.assertIsNone(res["citation_audit"])
            self.assertIn("IP-SAKTI Sahayak", res["answer"])

    # --------------------------------------------------------------------------
    # 6. FAREWELL
    # --------------------------------------------------------------------------
    def test_farewell(self):
        queries = ["bye", "goodbye", "see you", "take care"]
        for q in queries:
            intent = self.engine.classify_intent(q)
            self.assertEqual(intent["category"], "FAREWELL", f"Failed for '{q}': got {intent['category']}")
            
            res = self.engine.ask(q)
            self.assertEqual(res["category"], "FAREWELL")
            self.assertEqual(len(res["sources"]), 0)
            self.assertIsNone(res["citation_audit"])
            self.assertIn("goodbye", res["answer"].lower())

    # --------------------------------------------------------------------------
    # 7. MULTI-TURN: Greeting followed by AYUSH Question
    # --------------------------------------------------------------------------
    def test_greeting_followed_by_ayush_question(self):
        # Turn 1: Greeting
        t1 = self.engine.ask("Hello! Good morning")
        self.assertIn(t1["category"], {"GREETING", "TIME_GREETING"})
        self.assertEqual(len(t1["sources"]), 0)

        # Turn 2: AYUSH research question
        t2 = self.engine.ask("What phytochemicals are reported in Curcuma longa?")
        self.assertEqual(t2["category"], "AYUSH_RESEARCH")
        self.assertTrue(len(t2["sources"]) > 0, "Expected ChromaDB chunks for AYUSH question")
        self.assertIsNotNone(t2["citation_audit"])

    # --------------------------------------------------------------------------
    # 8. MULTI-TURN: AYUSH Question followed by Contextual Follow-up
    # --------------------------------------------------------------------------
    def test_ayush_question_followed_by_contextual_followup(self):
        # Turn 1: AYUSH question
        t1 = self.engine.ask("What are the therapeutic properties of Curcuma longa?")
        self.assertEqual(t1["category"], "AYUSH_RESEARCH")
        self.assertTrue(len(t1["sources"]) > 0)

        # Turn 2: Contextual follow-up with pronoun "it"
        t2 = self.engine.ask("Which Ayurvedic formulations contain it for skin disorders?")
        self.assertIn(t2["category"], {"FOLLOW_UP", "AYUSH_RESEARCH"})
        self.assertTrue(len(t2["sources"]) > 0)
        self.assertIsNotNone(t2["citation_audit"])

    # --------------------------------------------------------------------------
    # 9. BOUNDARY TESTS: Research questions containing conversational words
    # --------------------------------------------------------------------------
    def test_research_queries_with_conversational_words(self):
        test_cases = [
            ("High bioavailability curcumin formulations and piperine synergy", "AYUSH_RESEARCH"),
            ("Is it ok to combine turmeric with piperine under patent claims?", "AYUSH_RESEARCH"),
            ("Thanks to curcumin's anti-inflammatory properties, what are its indications?", "AYUSH_RESEARCH"),
            ("What are the bye-products of solvent extraction of haridra rhizome?", "AYUSH_RESEARCH")
        ]
        for query, expected_cat in test_cases:
            intent = self.engine.classify_intent(query)
            self.assertNotEqual(intent["category"], "GREETING", f"Query '{query}' wrongly treated as GREETING")
            self.assertNotEqual(intent["category"], "ACKNOWLEDGEMENT", f"Query '{query}' wrongly treated as ACKNOWLEDGEMENT")
            self.assertNotEqual(intent["category"], "GRATITUDE", f"Query '{query}' wrongly treated as GRATITUDE")
            self.assertNotEqual(intent["category"], "FAREWELL", f"Query '{query}' wrongly treated as FAREWELL")
            self.assertIn(intent["category"], {"AYUSH_RESEARCH", "FOLLOW_UP"})

    # --------------------------------------------------------------------------
    # 10. CLASSIFICATION FAILURE & SAFE FALLBACK
    # --------------------------------------------------------------------------
    def test_classification_failure_safe_fallback(self):
        # Simulate LLM classification failure (e.g. API error or malformed JSON)
        with patch("assistant_engine.generate_response", side_effect=Exception("API timeout simulation")):
            # Case A: Obvious conversational greeting
            res_hi = self.engine.classify_intent("hi")
            self.assertEqual(res_hi["category"], "GREETING")

            # Case B: Obvious acknowledgement
            res_ok = self.engine.classify_intent("ok")
            self.assertEqual(res_ok["category"], "ACKNOWLEDGEMENT")

            # Case C: Obvious time greeting
            res_tg = self.engine.classify_intent("good morning")
            self.assertEqual(res_tg["category"], "TIME_GREETING")

            # Case D: Obvious research query
            res_ayush = self.engine.classify_intent("What are the phytochemicals in Curcuma longa?")
            self.assertEqual(res_ayush["category"], "AYUSH_RESEARCH")

            # Case E: Ambiguous / uncertain query -> Must map safely to CLARIFICATION (not AYUSH_RESEARCH)
            res_uncertain = self.engine.classify_intent("perhaps maybe somewhere")
            self.assertEqual(res_uncertain["category"], "CLARIFICATION")
            
            # Verify ask() on CLARIFICATION triggers 0 retrieval
            ask_res = self.engine.ask("perhaps maybe somewhere")
            self.assertEqual(ask_res["category"], "CLARIFICATION")
            self.assertEqual(len(ask_res["sources"]), 0)
            self.assertIn("clarify", ask_res["answer"].lower())

    # --------------------------------------------------------------------------
    # 11. NO UNNECESSARY RETRIEVAL FOR CONVERSATIONAL QUERIES
    # --------------------------------------------------------------------------
    def test_no_retrieval_for_conversational_categories(self):
        conversational_samples = [
            ("hello", "GREETING"),
            ("good afternoon", "TIME_GREETING"),
            ("thanks a lot", "GRATITUDE"),
            ("got it, thanks", "GRATITUDE"),
            ("who are you?", "IDENTITY"),
            ("goodbye!", "FAREWELL")
        ]
        with patch("assistant_engine.retrieve_multi") as mock_retriever:
            for q, expected_cat in conversational_samples:
                res = self.engine.ask(q)
                self.assertEqual(len(res["sources"]), 0)
                self.assertIsNone(res["citation_audit"])
            mock_retriever.assert_not_called()

    # --------------------------------------------------------------------------
    # 12. MULTILINGUAL CONVERSATIONAL RESPONSES
    # --------------------------------------------------------------------------
    def test_multilingual_conversational_responses(self):
        # Hindi greeting
        res_hi = self.engine.ask("namaste", user_language="Hindi")
        self.assertTrue("सहायक" in res_hi["answer"] or "सहायता" in res_hi["answer"])
        self.assertEqual(len(res_hi["sources"]), 0)

        # Hindi gratitude
        res_hi_thanks = self.engine.ask("dhanyavad", user_language="Hindi")
        self.assertEqual(len(res_hi_thanks["sources"]), 0)

        # Telugu greeting
        res_te = self.engine.ask("namaskaram", user_language="Telugu")
        self.assertIn("నమస్కారం", res_te["answer"])
        self.assertEqual(len(res_te["sources"]), 0)


if __name__ == "__main__":
    unittest.main()
