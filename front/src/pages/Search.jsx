import React, { useState } from "react";
import ImageCard from "../components/ImageCard";
import { searchImages, uploadImages } from "../services/api";

export default function Search() {
  const [queryImage, setQueryImage] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [topK, setTopK] = useState(5);
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState([]);
  const [searchTime, setSearchTime] = useState(0);

  const handleImageSelect = (e) => {
    const file = e.target.files[0];

    if (!file) return;

    setQueryImage(file);
    setPreviewUrl(URL.createObjectURL(file)); //create a blob url for browser to see the image
    // Reset results when new image is picked
    setResults([]);
  };

  const clearImage = (e) => {
    e.stopPropagation();
    setQueryImage(null);
    setPreviewUrl(null);
    setResults([]);
  };

  /*
    Take the selected query image →
    send it to backend →
    receive similar images →
    adapt data →
    update UI state.
  */

  const handleSearch = async () => {
    if (!queryImage) return;
    setIsSearching(true);
    setResults([]);
    try {
      const start = performance.now();

      const uploadRes = await uploadImages(queryImage);

      // expected backend response:
      // { uploaded: [{ id, filename, url }] }
      const imageUrl = uploadRes?.uploaded?.[0]?.image_url;
      console.log("Uploaded image URL:", imageUrl);

      if (!imageUrl || typeof imageUrl !== "string") {
        throw new Error("Upload succeeded but image_url missing");
      }

      // 2️⃣ Search using image_url (JSON)
      const response = await searchImages(imageUrl, topK);

      const end = performance.now();
      setSearchTime(((end - start) / 1000).toFixed(2));

      // 3️⃣ Map backend results → UI format
      const mappedResults = response.results.map((item) => ({
        id: item.image_id,
        url: item.image_url,
        filename: item.filename,
        score: item.score,
      }));

      setResults(mappedResults);
    } catch (error) {
      console.error("Search failed:", error);
      alert("Search failed. Please try again.");
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto p-4 space-y-8">
      {/* HEADER */}
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Visual Search</h2>
        <p className="text-gray-500 mt-2 text-lg">
          Find similar images by uploading a reference photo.
        </p>
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        {/* LEFT COLUMN: Input & Controls */}
        <div className="lg:col-span-1 space-y-6">
          {/* SECTION 1: Query Upload */}
          <section className="bg-white p-6 rounded-xl border shadow-sm">
            <h3 className="font-semibold mb-4 text-gray-800">
              1. Upload Query Image
            </h3>

            <div className="relative group">
              <input
                type="file"
                id="query-upload"
                className="hidden"
                accept="image/*"
                onChange={handleImageSelect}
              />

              <label
                htmlFor="query-upload"
                className={`
                            block w-full rounded-lg border-2 border-dashed transition-all cursor-pointer overflow-hidden
                            ${previewUrl ? "border-indigo-500 h-64 bg-gray-900" : "border-gray-300 h-48 hover:border-indigo-400 hover:bg-indigo-50"}
                        `}
              >
                {previewUrl ? (
                  <div className="relative w-full h-full flex items-center justify-center">
                    <img
                      src={previewUrl}
                      alt="Query"
                      className="max-w-full max-h-full object-contain"
                    />
                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                      <button
                        onClick={clearImage}
                        className="bg-red-500 text-white px-4 py-2 rounded-full font-medium shadow-lg hover:bg-red-600 transform scale-90 group-hover:scale-100 transition-all"
                      >
                        Change Image
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-full text-gray-400">
                    <svg
                      className="w-10 h-10 mb-2"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                      />
                    </svg>
                    <span className="text-sm font-medium">
                      Click to select image
                    </span>
                  </div>
                )}
              </label>
            </div>
          </section>

          {/* SECTION 2: Controls */}
          <section className="bg-white p-6 rounded-xl border shadow-sm">
            <h3 className="font-semibold mb-4 text-gray-800">
              2. Search Settings
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Results (Top K)
                </label>
                <select
                  value={topK}
                  onChange={(e) => setTopK(Number(e.target.value))}
                  className="w-full border-gray-300 rounded-md shadow-sm focus:border-indigo-500 focus:ring-indigo-500 p-2 border"
                >
                  <option value={5}>5 Results</option>
                  <option value={10}>10 Results</option>
                  <option value={20}>20 Results</option>
                  <option value={30}>30 Results</option>
                  <option value={40}>40 Results</option>
                  <option value={50}>50 Results</option>
                </select>
              </div>
            </div>
          </section>

          <button
            onClick={handleSearch}
            disabled={!queryImage || isSearching}
            className={`
                    w-full py-3 rounded-lg font-medium shadow-lg transition-all flex items-center justify-center gap-2
                    ${
                      !queryImage || isSearching
                        ? "bg-gray-400 text-gray-200 cursor-not-allowed"
                        : "bg-indigo-600 text-white hover:bg-indigo-700 hover:shadow-indigo-500/30"
                    }
                `}
          >
            {isSearching ? (
              <>
                <svg
                  className="animate-spin h-5 w-5 text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                Searching...
              </>
            ) : (
              "Search Similar Images"
            )}
          </button>
        </div>

        {/* RIGHT COLUMN: Results Grid */}
        <div className="lg:col-span-2">
          {isSearching && (
            <div className="bg-white rounded-xl h-full border border-gray-100 shadow-sm p-8 flex flex-col items-center justify-center min-h-[300px] md:min-h-[500px]">
              <div className="w-16 h-16 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin mb-6"></div>
              <h3 className="text-xl font-semibold text-gray-800">
                Searching Visual Index...
              </h3>
              <p className="text-gray-500 mt-2">
                Analyzing image features & matching embeddings.
              </p>
            </div>
          )}

          {!isSearching && results.length > 0 && (
            <div className="space-y-6 animate-fade-in-up">
              <div className="flex justify-between items-end border-b pb-4">
                <h3 className="text-xl font-bold text-gray-800">
                  Search Results
                </h3>
                <span className="text-gray-500 text-sm">
                  Found {results.length} matches in {searchTime}s
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {results.map((result) => (
                  <ImageCard key={result.id} result={result} />
                ))}
              </div>
            </div>
          )}

          {!isSearching && results.length === 0 && (
            <div className="bg-gray-50 rounded-xl h-full border-2 border-dashed border-gray-200 flex flex-col items-center justify-center min-h-[300px] md:min-h-[500px] text-center p-8">
              <div className="bg-white p-4 rounded-full shadow-sm mb-4">
                <svg
                  className="w-12 h-12 text-gray-300"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-900">
                No results to show
              </h3>
              <p className="text-gray-500 max-w-sm mt-1">
                Upload an image from the left panel and set your preferences to
                start searching.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
