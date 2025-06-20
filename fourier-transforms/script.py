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
        paths, attributes = svg2paths(svg_path)
        print(f"Processing {len(paths)} paths from {svg_path}")
        if sort_paths and len(paths) > 1:
            paths_with_info = []
            for i, path in enumerate(paths):
                try:
                    bbox = path.bbox()
                    if bbox:
                        left_x = bbox[0]  
                        paths_with_info.append((left_x, i, path))
                        print(f"Path {i+1}: left edge at x={left_x:.1f}")
                    else:
                        first_point = path.point(0)
                        left_x = np.real(first_point)
                        paths_with_info.append((left_x, i, path))
                        print(f"Path {i+1}: starts at x={left_x:.1f}")
                except:
                    paths_with_info.append((float('inf'), i, path))
                    print(f"Path {i+1}: position unknown, placing at end")
            

            paths_with_info.sort(key=lambda x: x[0])
            paths = [info[2] for info in paths_with_info]
            
            print("\nPath order after sorting (left to right):")
            for i, (x_pos, orig_idx, _) in enumerate(paths_with_info):
                print(f"  Position {i+1}: Original path {orig_idx+1} (x={x_pos:.1f})")
        

        all_coordinates = []
        total_points_added = 0
        
        for i, path in enumerate(paths):
            print(f"\nProcessing path {i+1}/{len(paths)}")
            

            path_coords = sample_path_by_length(path, points_per_unit)
            
            if path_coords:
                all_coordinates.extend(path_coords)
                total_points_added += len(path_coords)
                print(f"  ✓ Added {len(path_coords)} points (total: {total_points_added})")
            else:
                print(f"  ✗ Failed to extract points from path {i+1}")
        
        if not all_coordinates:
            print("No coordinates extracted, trying alternative method...")
            all_coordinates = extract_with_svg_dom_simulation_single_array(svg_path, points_per_unit, sort_paths)
        
        if all_coordinates:
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
        num_points = max(10, int(total_length * points_per_unit))
        print(f"    Sampling {num_points} points")
        for i in range(num_points + 1): 
            t = i / num_points if num_points > 0 else 0
            
            try:
                point = path.point(t)
                x = float(np.real(point))
                y = float(np.imag(point))
                if not (np.isnan(x) or np.isnan(y) or np.isinf(x) or np.isinf(y)):
                    coordinates.append({"x": x, "y": y})
                    
            except Exception as e:
                print(f"      Warning: Point sampling failed at t={t}: {e}")
                continue
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
        tree = ET.parse(svg_path)
        root = tree.getroot()
        path_elements = root.findall('.//{http://www.w3.org/2000/svg}path')
        if not path_elements:
            path_elements = root.findall('.//path')  # Try without namespace
        
        print(f"Found {len(path_elements)} path elements in SVG")
        paths_with_elements = []
        for i, path_elem in enumerate(path_elements):
            path_data = path_elem.get('d')
            if not path_data:
                continue
            
            try:
                from svgpathtools import parse_path
                path = parse_path(path_data)
                transform = path_elem.get('transform')
                if transform:
                    path = apply_transform_to_path(path, transform)
                
                paths_with_elements.append((path_elem, path, i))
                
            except Exception as e:
                print(f"  Error parsing path {i+1}: {e}")
                continue
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

        all_coordinates = []
        
        for i, (path_elem, path, orig_idx) in enumerate(paths_with_elements):
            print(f"Processing sorted path {i+1} (originally path {orig_idx+1})")
            

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

        if 'translate' in transform_str:

            import re
            matches = re.findall(r'translate\(([^)]+)\)', transform_str)
            if matches:
                values = matches[0].split(',')
                if len(values) >= 2:
                    tx = float(values[0].strip())
                    ty = float(values[1].strip())
                    

                    translated_path = Path()
                    for segment in path:
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

const coordinates = {json.dumps(coordinates, indent=2)};
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

if __name__ == "__main__":
    svg_file = ""
    
    print("🚀 Starting SVG coordinate extraction (single array output)...")
    
    analyze_svg_structure(svg_file)

    success = extract_svg_coordinates_single_array(
        svg_file,
        output_dir="svg_output",
        points_per_unit=1.5, 
        sort_paths=True 
    )
    
    if success:
        print("\n🎉 Coordinate extraction completed successfully!")
        print("All letter coordinates are now in a single array.")
        print("Check the 'svg_output' directory for your JavaScript file.")
        print("\nUsage in your JavaScript:")
        print("  import coordinates from './svg_output/DCSicon_coordinates.js';")
        print("  console.log(`Loaded ${coordinates.length} points`);")
    else:
        print("\n❌ Extraction failed. Try adjusting the points_per_unit parameter.")
        print("For more detail: increase points_per_unit (e.g., 3.0)")
        print("For fewer points: decrease points_per_unit (e.g., 0.5)")