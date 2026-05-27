import { useRef, useState } from "react";

export default function ImageUploader({ onSelect, max = 9 }) {
  const inputRef = useRef(null);
  const [drag, setDrag] = useState(false);
  const [previews, setPreviews] = useState([]);

  function handle(files) {
    const arr = Array.from(files).slice(0, max);
    const next = arr.map((f) => ({ file: f, url: URL.createObjectURL(f) }));
    setPreviews(next);
    onSelect?.(arr);
  }

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          handle(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        className={`flex h-44 cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed text-center text-sm transition ${
          drag ? "border-brand-500 bg-brand-50" : "border-slate-300 hover:border-brand-500"
        }`}
      >
        <p className="font-medium">Drop product photos or click to browse</p>
        <p className="text-xs text-slate-500">Up to {max} images · JPG/PNG · max 10MB each</p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept="image/jpeg,image/png"
          className="hidden"
          onChange={(e) => handle(e.target.files)}
        />
      </div>
      {previews.length > 0 && (
        <div className="mt-3 grid grid-cols-3 gap-2 sm:grid-cols-6">
          {previews.map((p, i) => (
            <img
              key={i}
              src={p.url}
              alt=""
              className="aspect-square w-full rounded-md object-cover ring-1 ring-slate-200"
            />
          ))}
        </div>
      )}
    </div>
  );
}
