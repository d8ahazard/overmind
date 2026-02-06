type FileEvent = {
  path: string;
  type: string;
};

export default function FileDiff({ files }: { files: FileEvent[] }) {
  return (
    <section>
      <h3>File Changes</h3>
      <div style={{ border: "1px solid #eee", padding: 8, minHeight: 120 }}>
        {files.length === 0 && <p>No file changes yet.</p>}
        {files.map((file, index) => (
          <div key={index}>
            <strong>{file.type}</strong> - {file.path}
          </div>
        ))}
      </div>
    </section>
  );
}
