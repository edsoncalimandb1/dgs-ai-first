import { z } from "zod";

export const FeedbackInputSchema = z.object({
  queryId: z.string().uuid(),
  rating: z.enum(["correct", "incorrect", "incomplete"]),
  comment: z.string().max(500).optional(),
  agentId: z.string().min(1),
});

export const FeedbackOutputSchema = z.object({
  feedbackId: z.string().uuid(),
  status: z.enum(["recorded", "pending_review"]),
  recordedAt: z.string().datetime({ offset: true }),
});

export type FeedbackInput = z.infer<typeof FeedbackInputSchema>;
export type FeedbackOutput = z.infer<typeof FeedbackOutputSchema>;
