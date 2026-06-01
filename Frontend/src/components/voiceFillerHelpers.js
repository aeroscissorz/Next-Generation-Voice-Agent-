/**
 * Pure helper functions for voice filler prompt generation.
 *
 * The voice agent's system prompt already makes it say a contextual
 * narration phrase (e.g. "Let me pull up your billing...") before
 * every tool call. These fillers kick in AFTER that initial phrase,
 * so they should continue the narration naturally — describing what
 * the agent is doing as a follow-up to what it already said.
 */

/**
 * Builds the first filler prompt — fires ~3s after the tool call started.
 * Should continue the contextual narration from the initial response,
 * describing what the agent is doing in a way that connects to what
 * it already said.
 * @param {string} toolName - 'validate_user' or 'forward_to_backend'
 * @returns {string} The filler prompt text prefixed with [System: ...]
 */
export function buildFillerPrompt(toolName) {
  if (toolName === 'validate_user') {
    return '[System: You already told the caller you are verifying their account. Continue narrating what you are doing as a natural follow-up — describe the step you are on, like matching their details or pulling up their profile. Say ONE short sentence that connects to what you already said. Do not repeat yourself.]'
  }

  return '[System: You already told the caller you are looking into their request. Continue narrating what you are doing as a natural follow-up — describe the specific step, like going through their records or checking the details. Reference their actual topic. Say ONE short sentence that connects to what you already said. Do not repeat yourself.]'
}

/**
 * Builds a follow-up filler prompt — fires ~5s after the previous filler ended.
 * Should continue the narration thread, acknowledging the wait while still
 * describing progress.
 * @returns {string} The follow-up prompt text prefixed with [System: ...]
 */
export function buildFollowUpPrompt() {
  return '[System: The lookup is taking a bit longer. Continue narrating what you are doing — describe the next step or that you are almost done. Keep it connected to what you said before. Say ONE short sentence. Do not repeat anything you have already said.]'
}
