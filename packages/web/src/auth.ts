import { createHash } from "node:crypto";
import NextAuth from "next-auth";
import Google from "next-auth/providers/google";

declare module "next-auth" {
  interface Session {
    user: {
      id: string;
      name?: string | null;
      email?: string | null;
      image?: string | null;
    };
  }
}

/**
 * Generate a deterministic UUID v5 from a Google profile.sub string.
 *
 * Uses the URL namespace (6ba7b811-9dad-11d1-80b4-00c04fd430c8) and SHA-1
 * to produce a stable UUID that the backend can store as a native UUID type.
 */
function googleSubToUUID5(sub: string): string {
  // UUID v5 URL namespace as bytes
  const namespace = Buffer.from(
    "6ba7b8119dad11d180b400c04fd430c8",
    "hex",
  );
  const hash = createHash("sha1")
    .update(namespace)
    .update(sub)
    .digest();

  // Set version (5) and variant (RFC 4122)
  const bytes = Buffer.from(hash.subarray(0, 16));
  bytes[6] = (bytes[6] & 0x0f) | 0x50; // version 5
  bytes[8] = (bytes[8] & 0x3f) | 0x80; // variant RFC 4122

  const hex = bytes.toString("hex");
  return [
    hex.slice(0, 8),
    hex.slice(8, 12),
    hex.slice(12, 16),
    hex.slice(16, 20),
    hex.slice(20, 32),
  ].join("-");
}

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [Google],
  pages: {
    signIn: "/login",
  },
  session: {
    strategy: "jwt",
  },
  callbacks: {
    jwt({ token, account, profile }) {
      if (account && profile?.sub) {
        token.id = googleSubToUUID5(profile.sub);
      }
      return token;
    },
    session({ session, token }) {
      if (token.id && session.user) {
        session.user.id = token.id as string;
      }
      return session;
    },
  },
});
