"""
Pydantic AI integration for VayuAPI
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel


class PydanticAIAgent:
    """
    Pydantic AI agent integration.

    Provides structured LLM interactions with Pydantic validation.

    Example:
        ```python
        from vayuapi.ai import PydanticAIAgent
        from pydantic import BaseModel
        from pydantic_ai import Agent

        class UserQuery(BaseModel):
            question: str
            context: str = ""

        class Answer(BaseModel):
            response: str
            confidence: float

        agent = Agent("openai:gpt-4", result_type=Answer)
        ai_agent = PydanticAIAgent(agent)

        @app.post("/ai/query")
        async def query_ai(query: UserQuery):
            result = await ai_agent.run(query.question)
            return result
        ```
    """

    def __init__(self, agent: Any = None, model: str = "openai:gpt-4"):
        """
        Initialize Pydantic AI agent.

        Args:
            agent: Pydantic AI Agent instance
            model: Model identifier if agent not provided
        """
        self.agent = agent
        self.model = model

        if not agent:
            try:
                from pydantic_ai import Agent
                self.agent = Agent(model)
            except ImportError:
                print("Warning: pydantic-ai not installed")

    async def run(
        self,
        prompt: str,
        context: Dict[str, Any] = None
    ) -> Any:
        """
        Run agent with prompt.

        Args:
            prompt: User prompt
            context: Optional context dict

        Returns:
            Agent result
        """
        if not self.agent:
            return {"error": "Agent not configured"}

        try:
            result = await self.agent.run(prompt, deps=context)
            return result.data
        except Exception as e:
            return {"error": str(e)}

    async def run_sync(self, prompt: str, context: Dict[str, Any] = None) -> Any:
        """
        Run agent synchronously.

        Args:
            prompt: User prompt
            context: Optional context dict

        Returns:
            Agent result
        """
        if not self.agent:
            return {"error": "Agent not configured"}

        try:
            result = self.agent.run_sync(prompt, deps=context)
            return result.data
        except Exception as e:
            return {"error": str(e)}


class AIModelRouter:
    """
    Route requests to different AI models based on criteria.

    Example:
        ```python
        router = AIModelRouter()

        router.add_model("fast", "openai:gpt-3.5-turbo", cost=0.001)
        router.add_model("smart", "openai:gpt-4", cost=0.03)
        router.add_model("local", "ollama:llama2", cost=0)

        # Route based on criteria
        result = await router.route(
            prompt="Explain quantum computing",
            prefer_cost=False  # Prefer quality
        )
        ```
    """

    def __init__(self):
        self.models: Dict[str, Dict] = {}

    def add_model(
        self,
        name: str,
        model_id: str,
        cost: float = 0.0,
        speed: int = 5,
        quality: int = 5
    ):
        """
        Add model to router.

        Args:
            name: Model name
            model_id: Model identifier
            cost: Cost per 1K tokens
            speed: Speed rating (1-10)
            quality: Quality rating (1-10)
        """
        try:
            from pydantic_ai import Agent
            agent = Agent(model_id)

            self.models[name] = {
                "agent": agent,
                "model_id": model_id,
                "cost": cost,
                "speed": speed,
                "quality": quality
            }
        except ImportError:
            print(f"Warning: Could not create agent for {model_id}")

    async def route(
        self,
        prompt: str,
        prefer_cost: bool = True,
        prefer_speed: bool = False,
        context: Dict[str, Any] = None
    ) -> Any:
        """
        Route request to best model based on preferences.

        Args:
            prompt: User prompt
            prefer_cost: Prefer lower cost
            prefer_speed: Prefer faster models
            context: Optional context

        Returns:
            Model response
        """
        if not self.models:
            return {"error": "No models configured"}

        # Select best model
        best_model = None
        best_score = -1

        for name, info in self.models.items():
            score = 0
            if prefer_cost:
                score += (10 - info["cost"] * 10)
            if prefer_speed:
                score += info["speed"]
            else:
                score += info["quality"]

            if score > best_score:
                best_score = score
                best_model = name

        # Run with selected model
        if best_model:
            agent = self.models[best_model]["agent"]
            ai_agent = PydanticAIAgent(agent)
            return await ai_agent.run(prompt, context)

        return {"error": "No suitable model found"}
