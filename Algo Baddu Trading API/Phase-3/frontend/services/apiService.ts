// Service to talk to the backend. Don't ghost the server, bro.

const API_BASE = 'http://localhost:8000';

export const startBot = async (assetType: string) => {
  try {
    const response = await fetch(`${API_BASE}/start?asset_type=${assetType}`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error(`Failed to start: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Start Bot Failed - Is the server napping?", error);
    throw error;
  }
};

export const stopBot = async () => {
  try {
    const response = await fetch(`${API_BASE}/stop`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error(`Failed to stop: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Stop Bot Failed - Maybe it's over 9000?", error);
    throw error;
  }
};
