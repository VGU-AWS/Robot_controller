const output = document.getElementById("output");
const baseUrlInput = document.getElementById("baseUrl");

let baseUrl = window.location.origin;
baseUrlInput.value = baseUrl;

function writeOutput(title, payload) {
  output.textContent = `${title}\n\n${JSON.stringify(payload, null, 2)}`;
}

async function request(path, options = {}) {
  const url = `${baseUrl}${path}`;
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  let data;
  try {
    data = await response.json();
  } catch {
    data = { detail: "Non-JSON response" };
  }

  if (!response.ok) {
    throw { status: response.status, data };
  }

  return data;
}

document.getElementById("saveSettings").addEventListener("click", () => {
  baseUrl = baseUrlInput.value.trim() || window.location.origin;
  writeOutput("Settings updated", { baseUrl });
});

document.getElementById("registerUserBtn").addEventListener("click", async () => {
  try {
    const name = document.getElementById("userName").value.trim();
    const data = await request("/register/user", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
    writeOutput("User registered", data);
  } catch (error) {
    writeOutput("Register user failed", error);
  }
});

document.getElementById("registerRobotBtn").addEventListener("click", async () => {
  try {
    const name = document.getElementById("robotName").value.trim();
    const data = await request("/register/robot", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
    writeOutput("Robot registered", data);
  } catch (error) {
    writeOutput("Register robot failed", error);
  }
});

document.getElementById("claimRobotBtn").addEventListener("click", async () => {
  try {
    const userToken = document.getElementById("claimUserToken").value.trim();
    const robotToken = document.getElementById("claimRobotToken").value.trim();

    const data = await request("/user/claim-robot", {
      method: "POST",
      headers: { "X-User-Token": userToken },
      body: JSON.stringify({ robot_token: robotToken }),
    });
    writeOutput("Robot claimed", data);
  } catch (error) {
    writeOutput("Claim robot failed", error);
  }
});

document.getElementById("sendCommandBtn").addEventListener("click", async () => {
  try {
    const userToken = document.getElementById("sendUserToken").value.trim();
    const robotId = Number(document.getElementById("sendRobotId").value);
    const commandText = document.getElementById("commandText").value.trim();

    const data = await request("/user/send-command", {
      method: "POST",
      headers: { "X-User-Token": userToken },
      body: JSON.stringify({ robot_id: robotId, command_text: commandText }),
    });
    writeOutput("Command sent", data);
  } catch (error) {
    writeOutput("Send command failed", error);
  }
});

document.getElementById("pollBtn").addEventListener("click", async () => {
  try {
    const robotToken = document.getElementById("pollRobotToken").value.trim();
    const data = await request("/robot/poll", {
      headers: { "X-Robot-Token": robotToken },
    });
    writeOutput("Poll result", data);
  } catch (error) {
    writeOutput("Poll failed", error);
  }
});

document.getElementById("ackBtn").addEventListener("click", async () => {
  try {
    const robotToken = document.getElementById("ackRobotToken").value.trim();
    const commandId = Number(document.getElementById("ackCommandId").value);
    const data = await request("/robot/received", {
      method: "POST",
      headers: { "X-Robot-Token": robotToken },
      body: JSON.stringify({ command_id: commandId }),
    });
    writeOutput("Command acknowledged", data);
  } catch (error) {
    writeOutput("Acknowledge failed", error);
  }
});

document.getElementById("healthBtn").addEventListener("click", async () => {
  try {
    const data = await request("/health/db");
    writeOutput("Health check", data);
  } catch (error) {
    writeOutput("Health check failed", error);
  }
});
