import Link from "next/link";

export default function LandingPage() {
  return (
    <div
      style={{
        minHeight: "100dvh",
        backgroundColor: "#fbfbfa",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Nav */}
      <nav
        style={{
          borderBottom: "1px solid #eaeaea",
          backgroundColor: "#ffffff",
          height: 56,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          paddingLeft: 32,
          paddingRight: 32,
        }}
      >
        <span style={{ fontSize: 15, fontWeight: 600, color: "#111111", letterSpacing: "-0.02em" }}>
          Second PC
        </span>
        <Link
          href="/auth"
          style={{
            fontSize: 13,
            color: "#787774",
            textDecoration: "none",
            padding: "6px 12px",
            border: "1px solid #eaeaea",
            borderRadius: 6,
            transition: "color 0.15s, border-color 0.15s",
          }}
        >
          Sign in
        </Link>
      </nav>

      {/* Hero */}
      <section
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: "80px 32px",
          maxWidth: 960,
          margin: "0 auto",
          width: "100%",
        }}
      >
        {/* Eyebrow */}
        <p
          style={{
            fontSize: 11,
            fontFamily: '"Geist Mono", "SF Mono", monospace',
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "#787774",
            marginBottom: 20,
          }}
        >
          Private beta
        </p>

        {/* Headline */}
        <h1
          style={{
            fontSize: "clamp(36px, 5vw, 64px)",
            fontWeight: 700,
            letterSpacing: "-0.03em",
            lineHeight: 1.08,
            color: "#111111",
            maxWidth: 640,
            marginBottom: 24,
          }}
        >
          Your second computer.
          <br />
          Always on.
        </h1>

        {/* Sub */}
        <p
          style={{
            fontSize: 17,
            color: "#787774",
            lineHeight: 1.6,
            maxWidth: 480,
            marginBottom: 40,
          }}
        >
          A persistent Linux desktop running in your browser. An AI agent that lives inside it,
          next to your files.
        </p>

        {/* CTA */}
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <Link
            href="/auth"
            style={{
              display: "inline-block",
              backgroundColor: "#111111",
              color: "#ffffff",
              fontSize: 14,
              fontWeight: 500,
              padding: "10px 20px",
              borderRadius: 6,
              textDecoration: "none",
              transition: "background-color 0.15s",
            }}
          >
            Get started
          </Link>
          <span style={{ fontSize: 13, color: "#ababab" }}>No credit card required</span>
        </div>
      </section>

      {/* Feature row */}
      <section
        style={{
          borderTop: "1px solid #eaeaea",
          backgroundColor: "#ffffff",
          padding: "64px 32px",
        }}
      >
        <div
          style={{
            maxWidth: 960,
            margin: "0 auto",
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
            gap: 40,
          }}
        >
          <Feature
            title="Persistent workspace"
            body="Files you upload stay. The agent builds context over time. Pause the computer and resume exactly where you left off."
          />
          <Feature
            title="Real Linux desktop"
            body="Full XFCE environment. Terminal, file manager, Firefox. Stream it to any browser, interact in real time."
          />
          <Feature
            title="AI inside the machine"
            body="The agent runs in the same sandbox as your desktop. It can read your files, run commands, and see the screen."
          />
        </div>
      </section>

      {/* Footer */}
      <footer
        style={{
          borderTop: "1px solid #eaeaea",
          padding: "24px 32px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <span style={{ fontSize: 13, color: "#ababab" }}>Second PC</span>
        <span
          style={{ fontSize: 12, fontFamily: '"Geist Mono", monospace', color: "#cccccc" }}
        >
          private beta
        </span>
      </footer>
    </div>
  );
}

function Feature({ title, body }: { title: string; body: string }) {
  return (
    <div>
      <p
        style={{
          fontSize: 13,
          fontWeight: 600,
          color: "#111111",
          marginBottom: 8,
          letterSpacing: "-0.01em",
        }}
      >
        {title}
      </p>
      <p style={{ fontSize: 13, color: "#787774", lineHeight: 1.6 }}>{body}</p>
    </div>
  );
}
