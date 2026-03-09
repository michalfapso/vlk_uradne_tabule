import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  users: defineTable({
    name: v.optional(v.string()),
    image: v.optional(v.string()),
    email: v.optional(v.string()),
    emailVerificationTime: v.optional(v.number()),
    phone: v.optional(v.string()),
    phoneVerificationTime: v.optional(v.number()),
    isAnonymous: v.optional(v.boolean()),
  }).index("email", ["email"]),

  docTags: defineTable({
    userId: v.id("users"),
    docId: v.string(), // ID of the document from the scrapers
    tag: v.string(),   // e.g., "important", "unimportant", "noted"
    docDate: v.string(), // ISO date string of the document
  })
    .index("by_user", ["userId"])
    .index("by_doc", ["docId"])
    .index("by_user_doc", ["userId", "docId"]),
});

