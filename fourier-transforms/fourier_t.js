let time = 0
let path = []
let x = []
let y = []
let fourierY
let fourierX
let isPaused = false
let pauseStartTime = 0
let pauseDuration = 1000 

function dft(x){
    let X = []
    let N = x.length
    for(let k=0 ; k < N ; k++){
        let re=0
        let im =0 
        for(let n=0;n < N ;n++){
            let angle = ( TWO_PI *k*n)/N
            re+= x[n] * cos(angle)
            im-= x[n] * sin(angle)
        }
        re = re/N
        im = im/N
        
        let freq = k
        let amp = sqrt(re*re + im*im)
        let phase = atan2(im , re)
        X[k] ={ re, im , freq , amp , phase} ;
    }
    return X
}

function setup(){
    createCanvas(1500,1000)
    const skip = 5
    for(let i=0 ; i<drawing.length ; i+=skip){
        x.push(drawing[i].x)
        y.push(drawing[i].y)
     }
     fourierX = dft(x)
     fourierY = dft(y)

     fourierX.sort((a,b) => b.amp - a.amp)
     fourierY.sort((a,b) => b.amp - a.amp)
}

function epicycles(x,y,fourier,rotation){
      for(let i=0 ; i<fourier.length; i++){
    let pre_x = x
    let pre_y = y
    let freq = fourier[i].freq
    let radius = fourier[i].amp
    let phase = fourier[i].phase
    x += radius * cos(freq*time + phase + rotation)
    y += radius * sin(freq*time + phase + rotation)

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
  return createVector(x,y)
}

function draw(){
  background(0);
  
  if(isPaused){

    beginShape()
    noFill()
    stroke('red')
    strokeWeight(2)
    for(let i=0 ; i<path.length ; i++){
      vertex(path[i].x,path[i].y)
    }
    endShape()

    if(millis() - pauseStartTime > pauseDuration){
      isPaused = false
      time = 0
      path = []
    }
    return 
  }
  

  let vx = epicycles(width/2+200,300,fourierX,0)
  let vy = epicycles(500,height/2,fourierY,HALF_PI)
  let vec = createVector(vx.x , vy.y)

  path.unshift(vec)
  
  line(vx.x , vx.y , vec.x , vec.y)
  line(vy.x , vy.y , vec.x , vec.y)

  beginShape()
  noFill()
  stroke('red')
  strokeWeight(2)
  for(let i=0 ; i<path.length ; i++){
    vertex(path[i].x,path[i].y)
  }
  endShape()
  
  dt = TWO_PI / fourierY.length
  time += dt

  if(time > TWO_PI){
    isPaused = true
    pauseStartTime = millis()
  }
}