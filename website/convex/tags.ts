import { query, mutation } from "./_generated/server";
import { v } from "convex/values";
import { auth } from "./auth";

export const getTags = query({
  args: {
    docIds: v.optional(v.array(v.string())),
  },
  handler: async (ctx, args) => {
    const userId = await auth.getUserId(ctx);
    if (!userId) {
      return [];
    }

    if (args.docIds) {
      const tags = await Promise.all(
        args.docIds.map((docId) =>
          ctx.db
            .query("docTags")
            .withIndex("by_user_doc", (q) =>
              q.eq("userId", userId).eq("docId", docId)
            )
            .unique()
        )
      );
      return tags.filter((tag) => tag !== null);
    }

    return await ctx.db
      .query("docTags")
      .withIndex("by_user", (q) => q.eq("userId", userId))
      .collect();
  },
});

export const setTag = mutation({
  args: {
    docId: v.string(),
    tag: v.string(),
    docDate: v.string(),
  },
  handler: async (ctx, args) => {
    const userId = await auth.getUserId(ctx);
    if (!userId) {
      throw new Error("Not authenticated");
    }

    const existing = await ctx.db
      .query("docTags")
      .withIndex("by_user_doc", (q) =>
        q.eq("userId", userId).eq("docId", args.docId)
      )
      .unique();

    if (existing) {
      await ctx.db.patch(existing._id, {
        tag: args.tag,
        docDate: args.docDate,
      });
    } else {
      await ctx.db.insert("docTags", {
        userId,
        docId: args.docId,
        tag: args.tag,
        docDate: args.docDate,
      });
    }
  },
});
