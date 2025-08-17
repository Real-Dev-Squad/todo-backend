from pydantic import BaseModel, Field


class GenerateTeamCreationInviteCodeResponse(BaseModel):
    """Response model for team creation invite code generation endpoint.

    Attributes:
        code: The generated team creation invite code
        description: Optional description for the code
        message: Success or status message from the operation
    """

    code: str = Field(description="The generated team invite code")
    description: str | None = Field(None, description="Optional description for the code")
    message: str = Field(description="Success message confirming code generation")
