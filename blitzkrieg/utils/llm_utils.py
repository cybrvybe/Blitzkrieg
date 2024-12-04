import os
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
from ..class_instances.blitz_env_manager import blitz_env_manager
from ..ui_management.console_instance import console
from ..prompts.system.project_contextualizer import project_contextualizer_system_prompt,project_contextualizer_qa_system_prompt, mainstream_project_contextualizer_system_prompt, mainstream_project_contextualizer_qa_system_prompt
# Set up the Anthropic API key
anthropic_api_key = blitz_env_manager.get_global_env_var("ANTHROPIC_API_KEY")
anthropic = Anthropic(api_key=anthropic_api_key)

system_prompt_map = {
    'project_contextualizer': {
        'generator_system_prompt': project_contextualizer_system_prompt,
        'discriminator_system_prompt': project_contextualizer_qa_system_prompt,
        'rewriter_system_prompt': project_contextualizer_system_prompt
    },
    'mainstream_project_contextualizer': {
        'generator_system_prompt': mainstream_project_contextualizer_system_prompt,
        'discriminator_system_prompt': mainstream_project_contextualizer_qa_system_prompt
    }
}

def chat_with_agent_with_qa(system_prompt_key: str, user_prompt: str):
    try:
        generator_system_prompt = system_prompt_map[system_prompt_key]['generator_system_prompt']
        discriminator_system_prompt = system_prompt_map[system_prompt_key]['discriminator_system_prompt']
        rewriter_system_prompt = system_prompt_map[system_prompt_key]['rewriter_system_prompt']

        generator_agent_response = chat_with_agent(generator_system_prompt, user_prompt)
        if generator_agent_response:
            discriminator_agent_response = chat_with_agent(discriminator_system_prompt, generator_agent_response)
            if discriminator_agent_response:
                if rewriter_system_prompt:
                    rewriter_agent_response = chat_with_agent(rewriter_system_prompt, discriminator_agent_response + generator_agent_response + user_prompt)
                    if rewriter_agent_response:
                        return rewriter_agent_response
                    else:
                        console.handle_error("Failed to chat with agent")
                        return None
            return discriminator_agent_response
        else:
            console.handle_error("Failed to chat with agent")
            return None
    except Exception as e:
        console.handle_error(f"Failed to chat with agent with QA: {str(e)}")
        return None

def chat_with_agent(system_prompt: str, user_prompt):
    try:
        response = anthropic.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1000,
            stream=True,
            temperature=0,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_prompt
                        }
                    ]
                }
            ]
        )

        full_response = ""
        for chunk in response:
            if hasattr(chunk, 'type') and chunk.type == 'content_block_delta':
                if hasattr(chunk.delta, 'text'):
                    full_response += chunk.delta.text
        console.display_llm_system_chat_response_display(full_response)

        return full_response
    except Exception as e:
        console.handle_error(f"Failed to chat with agent: {str(e)}")
        return None


def summarize_project(user_prompt: str):
    chat_with_agent_with_qa('project_contextualizer', user_prompt)
    chat_with_agent_with_qa('mainstream_project_contextualizer', user_prompt)
    return None
