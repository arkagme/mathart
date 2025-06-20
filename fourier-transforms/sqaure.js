let time = 0
wave = []
let new_input
function setup(){
  createCanvas(1500,400)
  new_input = createInput()
}

function draw(){
  background(0);
  translate(400 ,200);

  let x = 0
  let y = 0

  val = new_input.value()

  for(let i=0 ; i<val; i++){
    let pre_x = x
    let pre_y = y
    n = (i*2)+1
    let radius = 100*((4/(n*PI)))
    x += radius * cos(n*time)
    y += radius * sin(n*time)


  stroke('yellow')
  strokeWeight(4)
  noFill();
  ellipse(pre_x,pre_y,radius*2)


  fill('red')
  stroke('red')
  strokeWeight(3)
  line(pre_x,pre_y,x,y)
  ellipse(x,y,12)

  }
  wave.unshift(y)
  translate(300 , 0)
  line(x-300 , y , 0 , wave[0])

  beginShape()
  noFill()
   for ( let i=0 ; i<wave.length ; i++){
     vertex(i,wave[i])
  }
  endShape()
  
  time+=0.035
  if(wave.length > 500){
    wave.pop()
  }


}