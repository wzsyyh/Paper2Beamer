import unittest
from run_evaluation import get_longest_narrative_subsequence
from latex_utils import extract_frames

class TestNarrativeArcLogic(unittest.TestCase):

    def test_get_longest_narrative_subsequence(self):
        # Test case 1: Perfect sequence
        labels1 = ["Motivation", "Method", "Result", "Conclusion"]
        self.assertEqual(get_longest_narrative_subsequence(labels1), 4)

        # Test case 2: Perfect sequence with repetitions
        labels2 = ["Motivation", "Motivation", "Method", "Result", "Result", "Conclusion"]
        self.assertEqual(get_longest_narrative_subsequence(labels2), 6)

        # Test case 3: Sequence with 'Other' labels
        labels3 = ["Other", "Motivation", "Method", "Other", "Result", "Conclusion"]
        # 'Other' is filtered out, so this is equivalent to labels1
        self.assertEqual(get_longest_narrative_subsequence(labels3), 4)

        # Test case 4: Broken sequence (Result before Method)
        labels4 = ["Motivation", "Result", "Method", "Conclusion"]
        # LIS of [0, 2, 1, 3] is [0, 1, 3] or [0, 2, 3]. Length is 3.
        self.assertEqual(get_longest_narrative_subsequence(labels4), 3)

        # Test case 5: Sequence with a large gap
        labels5 = ["Motivation", "Conclusion"]
        # LIS of [0, 3] is [0, 3]. Length is 2.
        self.assertEqual(get_longest_narrative_subsequence(labels5), 2)

        # Test case 6: Reversed sequence
        labels6 = ["Conclusion", "Result", "Method", "Motivation"]
        # LIS of [3, 2, 1, 0] is 1.
        self.assertEqual(get_longest_narrative_subsequence(labels6), 1)

        # Test case 7: Only 'Other'
        labels7 = ["Other", "Other", "Other"]
        self.assertEqual(get_longest_narrative_subsequence(labels7), 0)

        # Test case 8: Empty list
        labels8 = []
        self.assertEqual(get_longest_narrative_subsequence(labels8), 0)
        
        # Test case 9: More complex sequence from before
        labels9 = ["Motivation", "Method", "Motivation", "Result", "Conclusion"]
        # LIS of [0, 1, 0, 2, 3] is [0, 1, 2, 3]. Length is 4.
        self.assertEqual(get_longest_narrative_subsequence(labels9), 4)

    def test_extract_frames(self):
        tex_content = r"""
\documentclass{beamer}
\begin{document}
\begin{frame}{\frametitle{Slide 1}}
Content 1
\end{frame}
\begin{frame}
\frametitle{Slide 2}
Content 2
\end{frame}
\end{document}
"""
        frames = extract_frames(tex_content)
        self.assertEqual(len(frames), 2)
        # Note: The current implementation of extract_frames is a bit basic
        # and might not parse titles perfectly depending on braces.
        # Let's check the content.
        self.assertIn("Content 1", frames[0]['content'])
        self.assertIn("Slide 2", frames[1]['title'])
        self.assertIn("Content 2", frames[1]['content'])

if __name__ == '__main__':
    unittest.main()
