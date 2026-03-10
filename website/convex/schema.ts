import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";
import { authTables } from "@convex-dev/auth/server";

export default defineSchema({
  ...authTables,

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
