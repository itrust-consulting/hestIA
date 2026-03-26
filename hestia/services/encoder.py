
from typing import Optional, List, Dict, Any, Union

import os
import re
import math
import json
import Stemmer
from pathlib import Path
from collections import Counter

from hestia.schemas.api import DenseVector, SparseVector
from hestia.protocols.llm import LLMProvider
import hestia.settings as s


class DenseEncoder:

    def __init__(self, provider: LLMProvider, model=s.DEFAULT_EMB_MODEL):
        self.provider = provider
        self.default_model = model

    def encode(self, inputs: str | List[str], 
              model: str | None = None, 
              options: Optional[Dict[str, Any]] = None) -> List[List[float]]:
        inputs = [inputs] if isinstance(inputs, str) else inputs
        use_model = model or self.default_model
        resp = self.provider.embed(inputs, model=use_model, options=options)
        return DenseVector(vector=resp[0])
         
    
class SparseEncoder:
    
    def __init__(self, corpus_dir: Path = s.CORPUS_DIR):
        if not os.path.isdir(corpus_dir):
            raise ValueError(f"Corpus directory not found: {corpus_dir}")
        self.corpus_dir = corpus_dir
    
    def _get_corpus(self, corpus_name: str):
        #corpus_filepath = self.corpus_dir + "/" + corpus_name.strip().replace(" ", "_") + ".json"
        corpus_filepath = self.corpus_dir.joinpath("./" + corpus_name.strip().replace(" ", "_") + ".json")
        if not os.path.exists(corpus_filepath):
            raise ValueError(f"Corpus data for {corpus_name} at {corpus_filepath} not available.")
        with open(corpus_filepath, "r") as file:
            corpus = json.load(file)
            file.close()
        return corpus
    
    def _default_tokenize(self, query: str) -> list[str]:
        TOKEN_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9_./-]+")
        return TOKEN_RE.findall(query.lower())

    def _tokenize(self, texts: Union[str, List[str]],
                stemmer: Optional[Stemmer.Stemmer] = None):
        
        if isinstance(texts, str):
            texts = [texts]

        vocab = {}
        ids_per_text = []
        next_id = 0
        for text in texts:
            tokens = self._default_tokenize(text)
            if stemmer is not None:
                tokens = [stemmer.stemWord(t) for t in tokens]
            
            text_ids: List[int] =  []
            for tok in tokens:
                if tok in vocab:
                    text_ids.append(vocab[tok])
                else:
                    vocab[tok] = next_id
                    text_ids.append(next_id)
                    next_id += 1

            ids_per_text.append(text_ids)

        return ids_per_text, vocab

    def _compute_bm25_stats(self, corpus_token_index: List[List[int]], k1=1.5, b=0.75):
        N = len(corpus_token_index)
        doc_lens = [len(ids) for ids in corpus_token_index]
        avgdl = max(sum(doc_lens) / max(N, 1), 1.0)

        df = Counter()
        for ids in corpus_token_index:
            df.update(set(ids))

        def idf(tid: int) -> float:
            dfi = df.get(tid, 0)
            return math.log(1.0 + (N - dfi + 0.5) / (dfi + 0.5))

        return {"N": N, "avgdl": avgdl, "df": df, "idf": idf, "k1": k1, "b": b}

    def _build_sparse_vector(self, 
                             data: str, 
                             vocab: Dict[str, int], 
                             stats: Dict[str, Any], 
                             stemmer: Optional[Stemmer.Stemmer] = Stemmer.Stemmer("english")
                             ) -> SparseVector:
        
        _, t_vocab = self._tokenize(data, stemmer)
        
        indices = []
        values = []
        
        for tok in t_vocab:
            tid = vocab.get(tok)
            if tid is None:
                continue
            dfi = stats["idf"](int(tid))
            
            indices.append(int(tid))
            values.append(dfi)

        pairs = sorted(zip(indices, values), key=lambda x: x[0])
        indices, values = (list(t) for t in zip(*pairs)) if pairs else ([], [])
        return SparseVector(indices=indices, values=values)

    def encode(self, data: str, corpus_name: str) -> SparseVector:

        corpus = self._get_corpus(corpus_name)
        stats = self._compute_bm25_stats(corpus.get("indices"))
        vocab = corpus.get("vocab")
        return self._build_sparse_vector(data, vocab, stats, )