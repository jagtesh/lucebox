import importlib.util
import pathlib
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


analyze = load('analyze')
run = load('run')


class BenchmarkToolTests(unittest.TestCase):
    def test_summary_requires_exact_case_ids(self):
        def row(case):
            return dict(case=case, score={'completed':True, 'pass':True},
                        wall_seconds=1, prefill_ms=1, decode_ms=1,
                        total_tokens=1, reasoning_tokens_native=1,
                        vram_bytes_after=1)
        expected = {'one', 'two'}
        self.assertTrue(analyze.summarize([row('one'), row('two')], expected)['complete'])
        summary = analyze.summarize([row('one'), row('other')], expected)
        self.assertFalse(summary['complete'])
        self.assertEqual(summary['missing_cases'], ['two'])
        self.assertEqual(summary['unexpected_cases'], ['other'])

    def test_model_provenance_hashes_all_and_rejects_manifest_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            swift = root / 'swift.gguf'
            bonsai = root / 'bonsai.gguf'
            swift.write_bytes(b'swift')
            bonsai.write_bytes(b'bonsai')
            digest = run.sha256_file(bonsai)
            manifest = [{'file':bonsai.name, 'bytes':bonsai.stat().st_size, 'sha256':digest}]
            result = run.model_provenance({'swift-native':str(swift), 'bonsai-pq2':str(bonsai)}, manifest)
            self.assertEqual(result['swift-native']['sha256'], run.sha256_file(swift))
            self.assertEqual(result['bonsai-pq2']['sha256'], digest)
            manifest[0]['sha256'] = '0' * 64
            with self.assertRaises(RuntimeError):
                run.model_provenance({'bonsai-pq2':str(bonsai)}, manifest)


if __name__ == '__main__':
    unittest.main()
