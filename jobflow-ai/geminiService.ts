
import { GoogleGenAI, Type } from "@google/genai";

const getAI = () => {
  const apiKey = import.meta.env.VITE_GEMINI_API_KEY;
  if (!apiKey) {
    console.error("VITE_GEMINI_API_KEY is not set");
    return null;
  }
  return new GoogleGenAI({ apiKey });
};

export async function generateCoverLetter(jobDetails: any, userProfile: any) {
  const ai = getAI();
  if (!ai) return "Error: API Key missing. Please check your .env file.";

  try {
    const response = await ai.models.generateContent({
      model: 'gemini-3-flash-preview',
      contents: `Generate a professional cover letter for a ${jobDetails.position} role at ${jobDetails.company}. 
                 My skills: ${JSON.stringify(userProfile.skills)}. 
                 My experience: ${userProfile.experience}. 
                 Keep it concise, enthusiastic, and tailored to these requirements: ${jobDetails.requirements.join(', ')}.`,
      config: {
        systemInstruction: "You are a professional career coach and expert resume writer.",
      },
    });
    return response.text;
  } catch (error) {
    console.error("Gemini Error:", error);
    return "Error generating content. Please try again.";
  }
}

export async function suggestEmailResponse(emailContent: string, tone: 'Professional' | 'Enthusiastic' | 'Concise') {
  const ai = getAI();
  if (!ai) return "Error: API Key missing.";

  try {
    const response = await ai.models.generateContent({
      model: 'gemini-3-flash-preview',
      contents: `Suggest a ${tone} response to this email from a recruiter: "${emailContent}"`,
      config: {
        systemInstruction: "You are a professional assistant helping job seekers with communication.",
      },
    });
    return response.text;
  } catch (error) {
    console.error("Gemini Error:", error);
    return "Error generating suggestion.";
  }
}

export async function analyzeSkillsMatch(jobDesc: string, userSkills: any[]) {
  const ai = getAI();
  if (!ai) return { matchScore: 0, missingSkills: ["API Key Missing"] };

  try {
    const response = await ai.models.generateContent({
      model: 'gemini-3-flash-preview',
      contents: `Analyze the match between this job description and these user skills. 
                 Job: ${jobDesc}
                 Skills: ${JSON.stringify(userSkills)}
                 Return a JSON object with a matchScore (0-100) and missingSkills (array).`,
      config: {
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            matchScore: { type: Type.NUMBER },
            missingSkills: { type: Type.ARRAY, items: { type: Type.STRING } }
          },
          required: ["matchScore", "missingSkills"]
        }
      },
    });
    return JSON.parse(response.text);
  } catch (error) {
    return { matchScore: 50, missingSkills: [] };
  }
}
