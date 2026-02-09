
const OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions";

const getApiKey = () => {
  return import.meta.env.VITE_GEMINI_API_KEY || null;
};

async function postToOpenRouter(model: string, contents: string, systemInstruction?: string, temperature = 0.3, max_tokens = 1024) {
  const apiKey = getApiKey();
  if (!apiKey) throw new Error('API key missing');

  const messages: any[] = [];
  if (systemInstruction) messages.push({ role: 'system', content: systemInstruction });
  messages.push({ role: 'user', content: contents });

  const payload = {
    model,
    messages,
    temperature,
    max_tokens
  };

  const res = await fetch(OPENROUTER_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`
    },
    body: JSON.stringify(payload)
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`OpenRouter error ${res.status}: ${text}`);
  }

  const data = await res.json();
  // OpenRouter/OpenAI-style response
  if (data?.choices && data.choices.length > 0) {
    return data.choices[0].message?.content || data.choices[0].text || '';
  }
  return '';
}

export async function generateCoverLetter(jobDetails: any, userProfile: any) {
  const model = 'google/gemini-2.0-flash-001';
  const contents = `Generate a professional cover letter for a ${jobDetails.position} role at ${jobDetails.company}. My skills: ${JSON.stringify(userProfile.skills)}. My experience: ${userProfile.experience}. Keep it concise, enthusiastic, and tailored to these requirements: ${jobDetails.requirements?.join(', ') || ''}.`;
  try {
    const text = await postToOpenRouter(model, contents, 'You are a professional career coach and expert resume writer.', 0.3, 512);
    return text;
  } catch (e) {
    console.error('OpenRouter error:', e);
    return 'Error generating content. Please try again.';
  }
}

export async function suggestEmailResponse(emailContent: string, tone: 'Professional' | 'Enthusiastic' | 'Concise') {
  const model = 'google/gemini-2.0-flash-001';
  const contents = `Suggest a ${tone} response to this email from a recruiter: "${emailContent}"`;
  try {
    const text = await postToOpenRouter(model, contents, 'You are a professional assistant helping job seekers with communication.', 0.3, 256);
    return text;
  } catch (e) {
    console.error('OpenRouter error:', e);
    return 'Error generating suggestion.';
  }
}

export async function analyzeSkillsMatch(jobDesc: string, userSkills: any[]) {
  const model = 'google/gemini-2.0-flash-001';
  const contents = `Analyze the match between this job description and these user skills. Job: ${jobDesc} Skills: ${JSON.stringify(userSkills)} Return a JSON object with a matchScore (0-100) and missingSkills (array).`;
  try {
    const text = await postToOpenRouter(model, contents, undefined, 0.3, 512);
    try {
      return JSON.parse(text);
    } catch (e) {
      return { matchScore: 50, missingSkills: [] };
    }
  } catch (e) {
    console.error('OpenRouter error:', e);
    return { matchScore: 50, missingSkills: [] };
  }
}
