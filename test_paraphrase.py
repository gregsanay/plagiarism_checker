try:
    from transformers import pipeline
except ImportError:
    import pytest
    pytest.skip("Skipping paraphrase test: 'transformers' package is not installed.", allow_module_level=True)

paraphraser = pipeline("text2text-generation", model="Vamsi/T5_Paraphrase_Paws")
test_sentence = "The quick brown fox jumps over the lazy dog."
paraphrases = paraphraser(test_sentence, max_length=100, num_return_sequences=3)

for i, paraphrase in enumerate(paraphrases):
    print(f"Paraphrase {i+1}: {paraphrase['generated_text']}")
