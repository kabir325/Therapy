export default function LoadingScreen({ title = "Loading Therepy..." }) {
  return (
    <main className="center-screen">
      <div className="panel large-panel centered-panel">
        <div className="pulse-orb" />
        <h1>{title}</h1>
        <p>Preparing your private therapy space.</p>
      </div>
    </main>
  );
}
