from svgpathtools import svg2paths, Path
import numpy as np
import json
import os
from xml.etree import ElementTree as ET

def extract_svg_coordinates_single_array(svg_path: str, output_dir: str = "svg_output", 
                                       points_per_unit: float = 2.0, sort_paths: bool = True) -> bool:
    """
    SVG coordinate extraction that combines all paths into a single coordinate array
    """
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(svg_path))[0]
    
    try:
        # Load SVG paths
        paths, attributes = svg2paths(svg_path)
        print(f"Processing {len(paths)} paths from {svg_path}")
        
        # Sort paths by their horizontal position (left to right) if requested
        if sort_paths and len(paths) > 1:
            paths_with_info = []
            for i, path in enumerate(paths):
                try:
                    bbox = path.bbox()
                    if bbox:
                        left_x = bbox[0]  # leftmost x coordinate
                        paths_with_info.append((left_x, i, path))
                        print(f"Path {i+1}: left edge at x={left_x:.1f}")
                    else:
                        # Fallback: use first point
                        first_point = path.point(0)
                        left_x = np.real(first_point)
                        paths_with_info.append((left_x, i, path))
                        print(f"Path {i+1}: starts at x={left_x:.1f}")
                except:
                    # If we can't determine position, put at end
                    paths_with_info.append((float('inf'), i, path))
                    print(f"Path {i+1}: position unknown, placing at end")
            
            # Sort by x position (left to right)
            paths_with_info.sort(key=lambda x: x[0])
            paths = [info[2] for info in paths_with_info]
            
            print("\nPath order after sorting (left to right):")
            for i, (x_pos, orig_idx, _) in enumerate(paths_with_info):
                print(f"  Position {i+1}: Original path {orig_idx+1} (x={x_pos:.1f})")
        
        # Combine all coordinates into a single array
        all_coordinates = []
        total_points_added = 0
        
        for i, path in enumerate(paths):
            print(f"\nProcessing path {i+1}/{len(paths)}")
            
            # Get path coordinates using length-based sampling
            path_coords = sample_path_by_length(path, points_per_unit)
            
            if path_coords:
                # Add all coordinates from this path to the main array
                all_coordinates.extend(path_coords)
                total_points_added += len(path_coords)
                print(f"  ✓ Added {len(path_coords)} points (total: {total_points_added})")
            else:
                print(f"  ✗ Failed to extract points from path {i+1}")
        
        # Try alternative method if no coordinates extracted
        if not all_coordinates:
            print("No coordinates extracted, trying alternative method...")
            all_coordinates = extract_with_svg_dom_simulation_single_array(svg_path, points_per_unit, sort_paths)
        
        if all_coordinates:
            # Save to JavaScript file as single array
            js_file = f"{output_dir}/{base_name}_coordinates.js"
            save_coordinates_to_js_single_array(all_coordinates, js_file, len(paths))
            
            print(f"\n✅ SUCCESS!")
            print(f"   Total points: {len(all_coordinates)}")
            print(f"   Total paths combined: {len(paths)}")
            print(f"   Saved to: {js_file}")
            return True
        else:
            print("\n❌ FAILED: No coordinates could be extracted")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

def sample_path_by_length(path: Path, points_per_unit: float) -> list:
    """
    Sample path coordinates based on path length (similar to getPointAtLength)
    """
    coordinates = []
    
    try:
        total_length = path.length()
        if total_length <= 0:
            return coordinates
        
        print(f"    Path length: {total_length:.2f}")
        
        # Calculate number of points based on path length
        num_points = max(10, int(total_length * points_per_unit))
        print(f"    Sampling {num_points} points")
        
        # Sample points along the path using length-based intervals
        for i in range(num_points + 1):  # +1 to include endpoint
            # Calculate position along path (0 to 1)
            t = i / num_points if num_points > 0 else 0
            
            try:
                # Get point at parameter t
                point = path.point(t)
                
                # Convert complex number to x, y coordinates
                x = float(np.real(point))
                y = float(np.imag(point))
                
                # Check for valid coordinates
                if not (np.isnan(x) or np.isnan(y) or np.isinf(x) or np.isinf(y)):
                    coordinates.append({"x": x, "y": y})
                    
            except Exception as e:
                print(f"      Warning: Point sampling failed at t={t}: {e}")
                continue
        
        # Remove duplicate consecutive points
        coordinates = remove_duplicate_points(coordinates)
        
        return coordinates
        
    except Exception as e:
        print(f"    Path sampling error: {e}")
        return []

def extract_with_svg_dom_simulation_single_array(svg_path: str, points_per_unit: float, sort_paths: bool) -> list:
    """
    Alternative extraction method that combines all paths into single array
    """
    print("Using alternative SVG DOM simulation method...")
    
    try:
        # Parse SVG XML directly
        tree = ET.parse(svg_path)
        root = tree.getroot()
        
        # Find all path elements
        path_elements = root.findall('.//{http://www.w3.org/2000/svg}path')
        if not path_elements:
            path_elements = root.findall('.//path')  # Try without namespace
        
        print(f"Found {len(path_elements)} path elements in SVG")
        
        # Convert to paths and sort if needed
        paths_with_elements = []
        for i, path_elem in enumerate(path_elements):
            path_data = path_elem.get('d')
            if not path_data:
                continue
            
            try:
                from svgpathtools import parse_path
                path = parse_path(path_data)
                
                # Apply any transforms
                transform = path_elem.get('transform')
                if transform:
                    path = apply_transform_to_path(path, transform)
                
                paths_with_elements.append((path_elem, path, i))
                
            except Exception as e:
                print(f"  Error parsing path {i+1}: {e}")
                continue
        
        # Sort paths by horizontal position if requested
        if sort_paths and len(paths_with_elements) > 1:
            sorted_paths = []
            for path_elem, path, orig_idx in paths_with_elements:
                try:
                    bbox = path.bbox()
                    if bbox:
                        left_x = bbox[0]
                    else:
                        first_point = path.point(0)
                        left_x = np.real(first_point)
                    sorted_paths.append((left_x, path_elem, path, orig_idx))
                except:
                    sorted_paths.append((float('inf'), path_elem, path, orig_idx))
            
            sorted_paths.sort(key=lambda x: x[0])
            paths_with_elements = [(item[1], item[2], item[3]) for item in sorted_paths]
        
        # Combine all coordinates into single array
        all_coordinates = []
        
        for i, (path_elem, path, orig_idx) in enumerate(paths_with_elements):
            print(f"Processing sorted path {i+1} (originally path {orig_idx+1})")
            
            # Sample the path and add to main array
            coords = sample_path_by_length(path, points_per_unit)
            if coords:
                all_coordinates.extend(coords)
                print(f"  ✓ Added {len(coords)} points to main array")
        
        return all_coordinates
        
    except Exception as e:
        print(f"Alternative method failed: {e}")
        return []

def apply_transform_to_path(path: Path, transform_str: str) -> Path:
    """
    Apply SVG transform to path (basic implementation)
    """
    try:
        # Basic transform parsing - you might need to expand this
        if 'translate' in transform_str:
            # Extract translate values
            import re
            matches = re.findall(r'translate\(([^)]+)\)', transform_str)
            if matches:
                values = matches[0].split(',')
                if len(values) >= 2:
                    tx = float(values[0].strip())
                    ty = float(values[1].strip())
                    
                    # Apply translation to path
                    translated_path = Path()
                    for segment in path:
                        # This is a simplified translation - you might need more complex transform handling
                        translated_segment = segment
                        translated_path.append(translated_segment)
                    
                    return translated_path
    except:
        pass
    
    return path

def remove_duplicate_points(coordinates: list, tolerance: float = 0.1) -> list:
    """
    Remove consecutive duplicate points
    """
    if not coordinates:
        return coordinates
    
    filtered = [coordinates[0]]
    
    for coord in coordinates[1:]:
        last_coord = filtered[-1]
        dx = abs(coord["x"] - last_coord["x"])
        dy = abs(coord["y"] - last_coord["y"])
        
        if dx > tolerance or dy > tolerance:
            filtered.append(coord)
    
    return filtered

def save_coordinates_to_js_single_array(coordinates: list, filename: str, total_paths: int):
    """
    Save coordinates to JavaScript file as a single array
    """
    js_content = f"""// Generated coordinates from SVG - All paths combined
// Total points: {len(coordinates)}
// Original paths combined: {total_paths}

const coordinates = {json.dumps(coordinates, indent=2)};

// Export for use in other modules
export default coordinates;

// Alternative export for direct usage
window.svgCoordinates = coordinates;

// Helper functions
window.getTotalPoints = function() {{
    return coordinates.length;
}};

window.getCoordinatesSubset = function(startIndex, count) {{
    return coordinates.slice(startIndex, startIndex + count);
}};

// Log summary
console.log(`SVG coordinates loaded: ${{coordinates.length}} total points from ${{total_paths}} combined paths`);
"""
    
    with open(filename, 'w') as f:
        f.write(js_content)
    
    print(f"Single array coordinates saved to: {filename}")
    print(f"Total points in combined array: {len(coordinates)}")

def analyze_svg_structure(svg_path: str):
    """
    Analyze SVG structure to help debug extraction issues
    """
    print(f"\n=== SVG STRUCTURE ANALYSIS: {svg_path} ===")
    
    try:
        paths, attributes = svg2paths(svg_path)
        
        total_points = 0
        for i, path in enumerate(paths):
            length = path.length()
            segments = len(path)
            estimated_points = max(10, int(length * 2))
            total_points += estimated_points
            
            print(f"Path {i+1}: {segments} segments, length={length:.1f}, est. points={estimated_points}")
        
        print(f"\nEstimated total points when combined: {total_points}")
        print(f"SVG viewBox/dimensions analysis:")
        
        # Try to get SVG dimensions
        tree = ET.parse(svg_path)
        root = tree.getroot()
        
        width = root.get('width')
        height = root.get('height')
        viewbox = root.get('viewBox')
        
        print(f"  Width: {width}")
        print(f"  Height: {height}")
        print(f"  ViewBox: {viewbox}")
        
    except Exception as e:
        print(f"Analysis error: {e}")

# Main execution
if __name__ == "__main__":
    svg_file = "./assets/arkagme.svg"
    
    print("🚀 Starting SVG coordinate extraction (single array output)...")
    
    # First analyze the SVG structure
    analyze_svg_structure(svg_file)
    
    # Extract coordinates with all paths combined into single array
    success = extract_svg_coordinates_single_array(
        svg_file,
        output_dir="svg_output",
        points_per_unit=1.5,  # Adjust this value to control point density
        sort_paths=True      # This ensures left-to-right letter order before combining
    )
    
    if success:
        print("\n🎉 Coordinate extraction completed successfully!")
        print("All ARKA letter coordinates are now in a single array.")
        print("Check the 'svg_output' directory for your JavaScript file.")
        print("\nUsage in your JavaScript:")
        print("  import coordinates from './svg_output/DCSicon_coordinates.js';")
        print("  console.log(`Loaded ${coordinates.length} points for entire ARKA text`);")
        print("  // coordinates[0] = first point of 'A'")
        print("  // coordinates[coordinates.length-1] = last point of 'A' (final letter)")
    else:
        print("\n❌ Extraction failed. Try adjusting the points_per_unit parameter.")
        print("For more detail: increase points_per_unit (e.g., 3.0)")
        print("For fewer points: decrease points_per_unit (e.g., 0.5)")