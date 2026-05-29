"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";

type Mode = "signin" | "signup";

export default function AuthPage() {
  const [mode, setMode] = useState<Mode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const { signIn, signUp } = useAuth();
  const router = useRouter();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setInfo(null);
    setLoading(true);

    try {
      if (mode === "signin") {
        await signIn(email, password);
        router.push("/workspace");
      } else {
        const data = await signUp(email, password);
        if (data.session) {
          router.push("/workspace");
        } else {
          setInfo("Check your email to confirm your account, then sign in.");
          setMode("signin");
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      style={{
        minHeight: "100dvh",
        backgroundColor: "#fbfbfa",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
      }}
    >
      {/* Back link */}
      <div style={{ position: "absolute", top: 24, left: 32 }}>
        <Link
          href="/"
          style={{ fontSize: 13, color: "#787774", textDecoration: "none" }}
        >
          Second PC
        </Link>
      </div>

      <div
        style={{
          width: "100%",
          maxWidth: 360,
          backgroundColor: "#ffffff",
          border: "1px solid #eaeaea",
          borderRadius: 12,
          padding: 32,
        }}
      >
        {/* Header */}
        <h1
          style={{
            fontSize: 18,
            fontWeight: 600,
            color: "#111111",
            letterSpacing: "-0.02em",
            marginBottom: 4,
          }}
        >
          {mode === "signin" ? "Sign in" : "Create account"}
        </h1>
        <p style={{ fontSize: 13, color: "#787774", marginBottom: 28 }}>
          {mode === "signin"
            ? "Welcome back. Enter your credentials."
            : "Get started with Second PC."}
        </p>

        {/* Tab row */}
        <div
          style={{
            display: "flex",
            gap: 0,
            marginBottom: 24,
            borderBottom: "1px solid #eaeaea",
          }}
        >
          {(["signin", "signup"] as Mode[]).map((m) => (
            <button
              key={m}
              onClick={() => {
                setMode(m);
                setError(null);
                setInfo(null);
              }}
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                fontSize: 13,
                fontWeight: mode === m ? 600 : 400,
                color: mode === m ? "#111111" : "#787774",
                padding: "0 0 10px 0",
                marginRight: 20,
                borderBottom: mode === m ? "2px solid #111111" : "2px solid transparent",
                transition: "color 0.15s",
              }}
            >
              {m === "signin" ? "Sign in" : "Sign up"}
            </button>
          ))}
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div>
            <label
              htmlFor="email"
              style={{ display: "block", fontSize: 12, color: "#787774", marginBottom: 6, fontWeight: 500 }}
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={{
                width: "100%",
                padding: "9px 12px",
                border: "1px solid #eaeaea",
                borderRadius: 6,
                fontSize: 14,
                color: "#111111",
                backgroundColor: "#fbfbfa",
                outline: "none",
                transition: "border-color 0.15s",
              }}
              onFocus={(e) => (e.currentTarget.style.borderColor = "#111111")}
              onBlur={(e) => (e.currentTarget.style.borderColor = "#eaeaea")}
            />
          </div>

          <div>
            <label
              htmlFor="password"
              style={{ display: "block", fontSize: 12, color: "#787774", marginBottom: 6, fontWeight: 500 }}
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              autoComplete={mode === "signup" ? "new-password" : "current-password"}
              minLength={mode === "signup" ? 8 : undefined}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={{
                width: "100%",
                padding: "9px 12px",
                border: "1px solid #eaeaea",
                borderRadius: 6,
                fontSize: 14,
                color: "#111111",
                backgroundColor: "#fbfbfa",
                outline: "none",
                transition: "border-color 0.15s",
              }}
              onFocus={(e) => (e.currentTarget.style.borderColor = "#111111")}
              onBlur={(e) => (e.currentTarget.style.borderColor = "#eaeaea")}
            />
          </div>

          {error && (
            <p
              style={{
                fontSize: 12,
                color: "#9F2F2D",
                backgroundColor: "#FDEBEC",
                padding: "8px 12px",
                borderRadius: 6,
                margin: 0,
              }}
            >
              {error}
            </p>
          )}

          {info && (
            <p
              style={{
                fontSize: 12,
                color: "#346538",
                backgroundColor: "#EDF3EC",
                padding: "8px 12px",
                borderRadius: 6,
                margin: 0,
              }}
            >
              {info}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              backgroundColor: "#111111",
              color: "#ffffff",
              fontSize: 14,
              fontWeight: 500,
              padding: "10px 0",
              border: "none",
              borderRadius: 6,
              cursor: loading ? "not-allowed" : "pointer",
              opacity: loading ? 0.6 : 1,
              transition: "opacity 0.15s, background-color 0.15s",
              marginTop: 4,
            }}
            onMouseEnter={(e) => !loading && (e.currentTarget.style.backgroundColor = "#333333")}
            onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "#111111")}
          >
            {loading
              ? mode === "signin"
                ? "Signing in..."
                : "Creating account..."
              : mode === "signin"
              ? "Sign in"
              : "Create account"}
          </button>
        </form>
      </div>
    </div>
  );
}
