const fs = require('fs');

function csvToCoordinatesArray(csvFilePath, outputFilePath) {
    // Read the CSV file
    const csvData = fs.readFileSync(csvFilePath, 'utf8');
    
    // Split into lines and process each line
    const lines = csvData.trim().split('\n');
    
    const coordinates = lines.map(line => {
        const [x, y] = line.split(',').map(coord => parseInt(coord.trim()));
        return { x, y };
    });
    
    // Write to JavaScript file
    const jsContent = `const coordinates = ${JSON.stringify(coordinates, null, 2)};

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = coordinates;
}

// For browser use
if (typeof window !== 'undefined') {
    window.coordinates = coordinates;
}`;
    
    fs.writeFileSync(outputFilePath, jsContent);
    console.log(`Converted ${coordinates.length} coordinate points to ${outputFilePath}`);
    
    return coordinates;
}

// Usage
csvToCoordinatesArray('coordinates.csv', 'coordinates.js');