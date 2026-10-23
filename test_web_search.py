import unittest
from unittest.mock import Mock, patch
from web_search import generate_with_search, tool_query, search_web

RESULT = {'results': [{'title': 'Python', 'url': 'https://www.python.org/', 'snippet': 'Official site.'}]}


class SearchTests(unittest.TestCase):
    def test_automatic_tool_loop(self):
        complete = Mock(side_effect=['{"tool":"web_search","query":"Python"}', 'Python is a language [1].'])
        search = Mock(return_value=RESULT)
        answer = generate_with_search(complete, 'What is Python?', search=search)
        search.assert_called_once_with('Python')
        self.assertIn('<https://www.python.org/>', answer)
        self.assertTrue(any('TOOL_RESULT' in p for p in complete.call_args.args[0]))

    def test_forced_search(self):
        search = Mock(return_value=RESULT)
        generate_with_search(Mock(return_value='Answer [1].'), 'question', force_query='Python', search=search)
        search.assert_called_once_with('Python')

    def test_no_search(self):
        search = Mock()
        self.assertEqual(generate_with_search(lambda _: 'Hello!', 'Hi', search=search), 'Hello!')
        search.assert_not_called()

    def test_model_outage_keeps_retrieved_sources(self):
        answer = generate_with_search(Mock(side_effect=RuntimeError), 'question',
                                      force_query='Python', search=lambda _: RESULT)
        self.assertIn('temporarily unavailable', answer)
        self.assertIn('<https://www.python.org/>', answer)

    def test_budget(self):
        search = Mock(return_value=RESULT)
        answer = generate_with_search(lambda _: '{"tool":"web_search","query":"Python"}', 'question', search=search)
        self.assertEqual(search.call_count, 2)
        self.assertIn('search limit', answer)

    def test_no_results_or_outage(self):
        complete = Mock(side_effect=['{"tool":"web_search","query":"Python"}', 'Could not verify.'])
        self.assertEqual(generate_with_search(complete, 'question', search=lambda _: {'results': []}), 'Could not verify.')
        with patch('web_search.urlopen', side_effect=TimeoutError):
            self.assertIn('error', search_web('never-cached-timeout-query'))

    def test_validate_actions(self):
        for text in ['{"tool":"exec","query":"id"}', '{"tool":"web_search","query":[]}',
                     '{"tool":"web_search","query":"x","extra":true}', 'print(1)']:
            self.assertIsNone(tool_query(text))
        self.assertEqual(tool_query('```json\n{"tool":"web_search","query":"Python"}\n```'), 'Python')


if __name__ == '__main__':
    unittest.main()
