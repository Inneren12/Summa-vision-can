import InfographicFeed from "@/components/gallery/InfographicFeed";

export default function HomePage() {
  return (
    <main className="min-h-screen px-4 py-12 max-w-6xl mx-auto">
      <header className="mb-12 text-center">
        <h1 className="text-4xl font-bold text-neon-green mb-3">
          Summa Vision
        </h1>
        <p className="text-text-secondary text-lg">
          Canadian macroeconomic data — visualized for everyone.
        </p>
      </header>
      <InfographicFeed />
    </main>
  );
}
