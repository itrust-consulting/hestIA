from typing import Any, Dict, Iterator, List, Optional, Protocol, Union


class LLMProvider(Protocol):
    def embed(
        self,
        inputs: Union[str, List[str]],
        *,
        model: str | None,
        options: Optional[Dict[str, Any]] = None,
    ) -> List[List[float]]: ...

    def generate(
        self,
        prompt: str,
        *,
        model: str | None,
        options: Optional[Dict[str, Any]] = None,
        stream: bool = False,
    ) -> Union[str, Iterator[Dict[str, str]]]: ...

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        model: str | None,
        options: Optional[Dict[str, Any]] = None,
        stream: bool = False,
    ) -> Union[str, Iterator[Dict[str, str]]]: ...

    @property
    def models(self) -> dict: ...
