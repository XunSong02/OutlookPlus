const delay = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

export async function mockSendEmail(input: { to: string; subject: string; body: string }) {
  await delay(800);
  return {
    id: `sent_${Date.now()}`,
    to: input.to,
    subject: input.subject,
  };
}

export async function mockExecuteEmailAction(input: { emailId: string; action: string }) {
  await delay(700);
  return {
    emailId: input.emailId,
    action: input.action,
    status: 'ok' as const,
  };
}

export async function mockRunAiRequest(input: { emailId: string; prompt: string }) {
  await delay(1100);
  return {
    emailId: input.emailId,
    responseText: `I've processed your request: "${input.prompt}". Draft has been created.`,
  };
}
