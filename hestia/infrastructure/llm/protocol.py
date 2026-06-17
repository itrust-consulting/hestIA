from typing import Any, AsyncIterator, Dict, List, Optional, Protocol, Union


# @MRS-039
class LLMProvider(Protocol):
    async def embed(
        self,
        inputs: Union[str, List[str]],
        *,
        model: str | None,
        options: Optional[Dict[str, Any]] = None,
    ) -> List[List[float]]: ...

    async def generate(
        self,
        prompt: str,
        *,
        model: str | None,
        options: Optional[Dict[str, Any]] = None,
        stream: bool = False,
    ) -> Union[str, AsyncIterator[Dict[str, str]]]: ...

    async def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        model: str | None,
        options: Optional[Dict[str, Any]] = None,
        stream: bool = False,
    ) -> Union[str, AsyncIterator[Dict[str, str]]]: ...

    @property
    def models(self) -> dict: ...
