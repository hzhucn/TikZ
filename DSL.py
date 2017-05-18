from language import Rectangle,Circle,Line,AbsolutePoint,Number,Sequence
from utilities import *
from fastRender import fastRender
from render import render

import re


def reflectPoint(rx,ry,px,py):
    if rx != None: return (rx - px,py)
    if ry != None: return (px,ry - py)
    assert False
def reflect(x = None,y = None):
    def reflector(stuff):
        return stuff + [ o.reflect(x = x,y = y) for o in stuff ]
    return reflector
    
class line():
    def __init__(self, x1, y1, x2, y2, arrow = None, solid = None):
        self.arrow = arrow
        self.solid = solid
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
    def evaluate(self):
        return Line.absoluteNumbered(self.x1,
                                     self.y1,
                                     self.x2,
                                     self.y2,
                                     arrow = self.arrow,
                                     solid = self.solid)
    def reflect(self, x = None,y = None):
        (x1,y1) = reflectPoint(x,y,self.x1,self.y1)
        (x2,y2) = reflectPoint(x,y,self.x2,self.y2)
        if self.arrow:
            return line(x1,y1,x2,y2,arrow = True,solid = self.solid)
        else:
            (a,b) = min((x1,y1),(x2,y2))
            (c,d) = max((x1,y1),(x2,y2))
            return line(a,b,c,d,
                        arrow = False,
                        solid = self.solid)
        

class rectangle():
    def __init__(self, x1, y1, x2, y2):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
    def evaluate(self):
        return Rectangle.absolute(self.x1,self.y1,self.x2,self.y2)
    
    def reflect(self, x = None,y = None):
        (x1,y1) = reflectPoint(x,y,self.x1,self.y1)
        (x2,y2) = reflectPoint(x,y,self.x2,self.y2)
        return rectangle(min(x1,x2),
                         min(y1,y2),
                         max(x1,x2),
                         max(y1,y2))

class circle():
    def __init__(self,x,y):
        self.x = x
        self.y = y
    def evaluate(self):
        return Circle(center = AbsolutePoint(Number(self.x),Number(self.y)),
                      radius = Number(1))
    def reflect(self, x = None,y = None):
        return circle(*reflectPoint(x,y,self.x,self.y))

def addFeatures(fs):
    composite = {}
    for f in fs:
        for k in f:
            composite[k] = composite.get(k,0) + f[k]
    return composite

class Reflection():
    def pretty(self):
        return "reflect(%s){\n%s\n}"%(self.command,self.body.pretty())
    def __init__(self, command, body):
        self.command = command
        self.body = body
    def hoistReflection(self):
        for j,p in enumerate(self.body.items):
            if isinstance(p,Primitive):
                newBlock = list(self.body.items)
                del newBlock[j]
                newBlock = Block(newBlock)
                yield Block([p,Reflection(self.command,newBlock)])
                
    def __str__(self):
        return "Reflection(%s,%s)"%(self.command,self.body)
    def convertToPython(self):
        return "%s(%s)"%(self.command, self.body.convertToPython())
    def extrapolations(self):
        for b in self.body.extrapolations():
            yield Reflection(self.command, b)
    def explode(self):
        return Reflection(self.command, self.body.explode())
    def features(self):
        return addFeatures([{'reflections':1,
                             'reflectionsX':int('x' in self.command),
                             'reflectionsY':int('y' in self.command)},
                            self.body.features()])
class Primitive():
    def pretty(self): return self.k
    def __init__(self, k): self.k = k
    def __str__(self): return "Primitive(%s)"%self.k
    def hoistReflection(self):
        return
        yield
    def convertToPython(self): return "[%s]"%self.k
    def extrapolations(self): yield self
    def explode(self):
        return self
    def features(self):
        return {'primitives':1,
                'lines':int('line' in self.k),
                'rectangle':int('rectangle' in self.k),
                'circles':int('circle' in self.k)}
class Loop():
    def pretty(self):
        p = "for (%s < %s){\n"%(self.v,self.bound)
        if self.boundary != None:
            p += "if (%s > 0){\n%s\n}"%(self.v,self.boundary.pretty())
        p += "%s\n}"%(self.body.pretty())
        return p
    def __init__(self, v, bound, body, boundary = None, lowerBound = 0):
        self.v = v
        self.bound = bound
        self.body = body
        self.boundary = boundary
        self.lowerBound = lowerBound
    def hoistReflection(self):
        for h in self.body.hoistReflection():
            yield Loop(self.v,self.bound,h,boundary = self.boundary,lowerBound = self.lowerBound)
        if self.boundary != None:
            for h in self.boundary.hoistReflection():
                yield Loop(self.v,self.bound,self.body,boundary = h,lowerBound = self.lowerBound)
                
    def __str__(self):
        if self.boundary != None:
            return "Loop(%s, %s, %s, %s, boundary = %s)"%(self.v,self.lowerBound, self.bound,self.body,self.boundary)
        return "Loop(%s, %s, %s, %s)"%(self.v,self.lowerBound, self.bound,self.body)
    def convertToPython(self):
        body = self.body.convertToPython()
        if self.boundary != None:
            body += " + ((%s) if %s > %s else %s)"%(self.boundary.convertToPython(),
                                                    self.v,
                                                    self.lowerBound,
                                                    '[]')
            
        return "[ _%s for %s in range(%s,%s) for _%s in (%s) ]"%(self.v,
                                                               self.v,
                                                               self.lowerBound,
                                                               self.bound,
                                                               self.v,
                                                               body)
        
    def extrapolations(self):
        for b in self.body.extrapolations():
            for boundary in ([None] if self.boundary == None else self.boundary.extrapolations()):
                for ub,lb in [(1,1),(1,0),(0,1),(0,0)]:
                    yield Loop(self.v, '%s + %d'%(self.bound,ub), b,
                               lowerBound = self.lowerBound - lb,
                               boundary = boundary)
    def explode(self):
        shrapnel = [ Loop(self.v,self.bound,bodyExpression.explode(),lowerBound = self.lowerBound)
                       for bodyExpression in self.body.items ]
        if self.boundary != None:
            shrapnel += [ Loop(self.v,self.bound,Block([]),lowerBound = self.lowerBound,
                               boundary = bodyExpression.explode())
                       for bodyExpression in self.boundary.items ]
        return Block(shrapnel)
    def features(self):
        f2 = int(str(self.bound) == '2')
        f3 = int(str(self.bound) == '3')
        f4 = int(str(self.bound) == '4')
        return addFeatures([{'loops':1,
                             '2': f2,
                             '3': f3,
                             '4': f4,
                             'boundary': int(self.boundary != None),
                             'variableLoopBound': int(f2 == 0 and f3 == 0 and f4 == 0)},
                            self.body.features(),
                            self.boundary.features() if self.boundary != None else {}])                             
                
class Block():
    def pretty(self): return ";\n".join([x.pretty() for x in self.items ])
    def convertToSequence(self):
        return Sequence([ p.evaluate() for p in eval(self.convertToPython()) ])
    def __init__(self, items): self.items = items
    def __str__(self): return "Block([%s])"%(", ".join(map(str,self.items)))
    def convertToPython(self):
        if self.items == []: return "[]"
        return " + ".join([ x.convertToPython() for x in self.items ])
    def extrapolations(self):
        if self.items == []: yield self
        else:
            for e in self.items[0].extrapolations():
                for s in Block(self.items[1:]).extrapolations():
                    yield Block([e] + s.items)
    def explode(self):
        return Block([ x.explode() for x in self.items ])
    def features(self):
        return addFeatures([ x.features() for x in self.items ])
    def hoistReflection(self):
        for j,x in enumerate(self.items):
            for y in x.hoistReflection():
                copy = list(self.items)
                copy[j] = y
                yield Block(copy)

    def fixReflections(self,target):
        distance = self.convertToSequence() - target
        if distance == 0: return self

        print "Fixing reflections"

        candidates = [self] + list(self.hoistReflection())
        sequences = [k.convertToSequence() for k in candidates ]
        distances = [target - s for s in sequences ]
        best = min(range(len(distances)),key = lambda k: distances[k])
        if distances[best] == distance: return self
        return candidates[best].fixReflections(target)
            

# return something that resembles a syntax tree, built using the above classes
def parseSketchOutput(output, environment = None, loopDepth = 0, coefficients = None):
    commands = []
    # variable bindings introduced by the sketch: we have to resolve them
    environment = {} if environment == None else environment

    # global coefficients for linear transformations
    coefficients = {} if coefficients == None else coefficients

    output = output.split('\n')

    def getBlock(name, startingIndex, startingDepth = 0):
        d = startingDepth

        while d > -1:
            if 'dummyStart' in output[startingIndex] and name in output[startingIndex]:
                d += 1
            elif 'dummyEnd' in output[startingIndex] and name in output[startingIndex]:
                d -= 1
            startingIndex += 1

        return startingIndex

    def getBoundary(startingIndex):
        while True:
            if 'dummyStartBoundary' in output[startingIndex]:
                return getBlock('Boundary', startingIndex + 1)
            if 'dummyStartLoop' in output[startingIndex]:
                return None
            if 'dummyEndLoop' in output[startingIndex]:
                return None
            startingIndex += 1
                

    j = 0
    while j < len(output):
        l = output[j]
        if 'void renderSpecification' in l: break

        m = re.search('validate[X|Y]\((.*), (.*)\);',l)
        if m:
            environment[m.group(2)] = m.group(1)
            j += 1
            continue

        m = re.search('int\[[0-9]\] coefficients([1|2]) = {([,0-9\-]+)};',l)
        if m:
            coefficients[int(m.group(1))] = map(int,m.group(2).split(","))
        
        # apply the environment
        for v in sorted(environment.keys(), key = lambda v: -len(v)):
            l = l.replace(v,environment[v])

        # Apply the coefficients
        if 'coefficients' in l:
            for k in coefficients:
                for coefficientIndex,coefficientValue in enumerate(coefficients[k]):
                    pattern = '\(coefficients%s[^\[]*\[%d\]\)'%(k,coefficientIndex)
                    # print "Substituting the following pattern",pattern
                    # print "For the following value",coefficientValue
                    lp = re.sub(pattern, str(coefficientValue), l)
                    # if l != lp:
                    #     print "changed it to",lp
                    l = lp
        
        pattern = '\(\(\(shapeIdentity == 0\) && \(cx.* == (.+)\)\) && \(cy.* == (.+)\)\)'
        m = re.search(pattern,l)
        if m:
            x = parseExpression(m.group(1))
            y = parseExpression(m.group(2))
            commands += [Primitive('circle(%s,%s)'%(x,y))]
            j += 1
            continue

        pattern = 'shapeIdentity == 1\) && \((.*) == lx1.*\)\) && \((.*) == ly1.*\)\) && \((.*) == lx2.*\)\) && \((.*) == ly2.*\)\) && \(([01]) == dashed\)\) && \(([01]) == arrow'
        m = re.search(pattern,l)
        if m:
            if False:
                print "Reading line!"
                print l
                for index in range(5): print "index",index,"\t",m.group(index),'\t',parseExpression(m.group(index))
            commands += [Primitive('line(%s,%s,%s,%s,arrow = %s,solid = %s)'%(parseExpression(m.group(1)),
                                                                              parseExpression(m.group(2)),
                                                                              parseExpression(m.group(3)),
                                                                              parseExpression(m.group(4)),
                                                                              m.group(6) == '1',
                                                                              m.group(5) == '0'))]
            j += 1
            continue
        

        pattern = '\(\(\(\(\(shapeIdentity == 2\) && \((.+) == rx1.*\)\) && \((.+) == ry1.*\)\) && \((.+) == rx2.*\)\) && \((.+) == ry2.*\)\)'
        m = re.search(pattern,l)
        if m:
            # print m,m.group(1),m.group(2),m.group(3),m.group(4)
            commands += [Primitive('rectangle(%s,%s,%s,%s)'%(parseExpression(m.group(1)),
                                                             parseExpression(m.group(2)),
                                                             parseExpression(m.group(3)),
                                                             parseExpression(m.group(4))))]
            j += 1
            continue

        pattern = 'for\(int (.*) = 0; .* < (.*); .* = .* \+ 1\)'
        m = re.search(pattern,l)
        if m and (not ('reflectionIndex' in m.group(1))):
            boundaryIndex = getBoundary(j + 1)
            if boundaryIndex != None:
                boundary = "\n".join(output[(j+1):boundaryIndex])
                boundary = parseSketchOutput(boundary, environment, loopDepth + 1, coefficients)
                j = boundaryIndex
            else:
                boundary = None
            
            bodyIndex = getBlock('Loop', j+1)
            body = "\n".join(output[(j+1):bodyIndex])
            j = bodyIndex

            bound = parseExpression(m.group(2))
            body = parseSketchOutput(body, environment, loopDepth + 1, coefficients)
            v = ['i','j'][loopDepth]
            commands += [Loop(v, bound, body, boundary)]
            continue

        pattern = 'dummyStartReflection\(([0-9]+), ([0-9]+)\)'
        m = re.search(pattern,l)
        if m:
            bodyIndex = getBlock('Reflection', j+1)
            body = "\n".join(output[(j+1):bodyIndex])
            j = bodyIndex
            x = int(m.group(1))
            y = int(m.group(2))
            k = 'reflect(%s = %d)'%('x' if y == 0 else 'y',
                                    max([x,y]))
            commands += [Reflection(k,
                                    parseSketchOutput(body, environment, loopDepth, coefficients))]

        j += 1
            
        
    return Block(commands)

def parseExpression(e):
    try: return int(e)
    except:
        factor = re.search('([\-0-9]+) * ',e)
        if factor != None: factor = int(factor.group(1))
        offset = re.search(' \+ ([\-0-9]+)',e)
        if offset != None: offset = int(offset.group(1))
        variable = re.search('\[(\d)\]',e)
        if variable != None: variable = ['i','j'][int(variable.group(1))]

        if factor == None:
            factor = 1
        if offset == None: offset = 0
        if variable == None:
            print e
            assert False

        if factor == 0: return str(offset)

        representation = variable
        if factor != 1: representation = "%d*%s"%(factor,representation)

        if offset != 0: representation += " + %d"%offset

        return representation

        # return "%s * %s + %s"%(str(factor),
        #                        str(variable),
        #                        str(offset))


def renderEvaluation(s, exportTo = None):
    parse = evaluate(eval(s))
    x0 = min([x for l in parse.lines for x in l.usedXCoordinates()  ])
    y0 = min([y for l in parse.lines for y in l.usedYCoordinates()  ])
    x1 = max([x for l in parse.lines for x in l.usedXCoordinates()  ])
    y1 = max([y for l in parse.lines for y in l.usedYCoordinates()  ])

    render([parse.TikZ()],showImage = exportTo == None,exportTo = exportTo,canvas = (x1+1,y1+1), x0y0 = (x0 - 1,y0 - 1))

if __name__ == '__main__':
    e = parseSketchOutput('''
void render (int shapeIdentity, int cx, int cy, int lx1, int ly1, int lx2, int ly2, bit dashed, bit arrow, int rx1, int ry1, int rx2, int ry2, ref bit _out)  implements renderSpecification/*tmpn1L3R8.sk:206*/
{
  _out = 0;
  assume (((shapeIdentity == 0) || (shapeIdentity == 1)) || (shapeIdentity == 2)): "Assume at tmpn1L3R8.sk:207"; //Assume at tmpn1L3R8.sk:207
  assume (shapeIdentity != 2): "Assume at tmpn1L3R8.sk:209"; //Assume at tmpn1L3R8.sk:209
  assume (!(dashed)): "Assume at tmpn1L3R8.sk:213"; //Assume at tmpn1L3R8.sk:213
  assume (arrow): "Assume at tmpn1L3R8.sk:215"; //Assume at tmpn1L3R8.sk:215
  int[2] coefficients1 = {3,4};
  int[0] environment = {};
  int[1] coefficients1_0 = coefficients1[0::1];
  int x_s36 = 0;
  validateX(4, x_s36);
  int y_s40 = 0;
  validateY(10, y_s40);
  bit inScene_s9 = 0 || (((shapeIdentity == 0) && (cx == x_s36)) && (cy == y_s40));
  dummyStartLoop();
  bit _pac_sc_s12 = inScene_s9;
  int newCost = 1;
  if(!(inScene_s9))/*tmpn1L3R8.sk:75*/
  {
    int loop_body_cost = 0;
    bit _pac_sc_s12_s14 = 0;
    for(int j = 0; j < 3; j = j + 1)/*Canonical*/
    {
      assert (j < 4); //Assert at tmpn1L3R8.sk:95 (-7295508099401847869)
      bit _pac_sc_s28 = _pac_sc_s12_s14;
      if(!(_pac_sc_s12_s14))/*tmpn1L3R8.sk:102*/
      {
        int[1] _pac_sc_s28_s30 = {0};
        push(0, environment, j, _pac_sc_s28_s30);
        int x_s36_0 = 0;
        validateX(((coefficients1_0[0]) * (_pac_sc_s28_s30[0])) + 1, x_s36_0);
        int y_s40_0 = 0;
        validateY(4, y_s40_0);
        int x2_s44 = 0;
        validateX(((coefficients1_0[0]) * (_pac_sc_s28_s30[0])) + 1, x2_s44);
        int y2_s48 = 0;
        validateY(2, y2_s48);
        bit _pac_sc_s28_s32 = 0 || (((((((shapeIdentity == 1) && (x_s36_0 == lx1)) && (y_s40_0 == ly1)) && (x2_s44 == lx2)) && (y2_s48 == ly2)) && (0 == dashed)) && (1 == arrow));
        bit _pac_sc_s15 = _pac_sc_s28_s32;
        int newCost_0 = 1;
        if(!(_pac_sc_s28_s32))/*tmpn1L3R8.sk:81*/
        {
          int ly2_0 = ly2;
          int ly1_0 = ly1;
          int cy_0 = cy;
          dummyStartReflection(0, 6);
          int reflection_cost = 0;
          bit _pac_sc_s15_s17 = 0;
          for(int reflectionIndex = 0; reflectionIndex < 2; reflectionIndex = reflectionIndex + 1)/*Canonical*/
          {
            if(reflectionIndex == 1)/*tmpn1L3R8.sk:160*/
            {
              cy_0 = 6 - (cy_0 - 0);
              if(arrow)/*tmpn1L3R8.sk:174*/
              {
                ly1_0 = 6 - (ly1_0 - 0);
                ly2_0 = 6 - (ly2_0 - 0);
              }
              else
              {
                int _ly1 = ly1_0;
                if(lx2 == lx1)/*tmpn1L3R8.sk:185*/
                {
                  ly1_0 = 6 - (ly2_0 - 0);
                  ly2_0 = 6 - (_ly1 - 0);
                }
                else
                {
                  ly1_0 = 6 - (ly1_0 - 0);
                  ly2_0 = 6 - (ly2_0 - 0);
                }
              }
            }
            bit _pac_sc_s18 = _pac_sc_s15_s17;
            if(!(_pac_sc_s15_s17))/*tmpn1L3R8.sk:196*/
            {
              int x_s36_1 = 0;
              validateX(((coefficients1_0[0]) * (_pac_sc_s28_s30[0])) + 1, x_s36_1);
              int y_s40_1 = 0;
              validateY(1, y_s40_1);
              bit _pac_sc_s18_s20 = 0 || (((shapeIdentity == 0) && (cx == x_s36_1)) && (cy_0 == y_s40_1));
              int x_s36_2 = 0;
              validateX(4, x_s36_2);
              int y_s40_2 = 0;
              validateY(9, y_s40_2);
              int x2_s44_0 = 0;
              validateX(((coefficients1_0[0]) * (_pac_sc_s28_s30[0])) + 1, x2_s44_0);
              int y2_s48_0 = 0;
              validateY(6, y2_s48_0);
              reflection_cost = 2;
              _pac_sc_s18_s20 = _pac_sc_s18_s20 || (((((((shapeIdentity == 1) && (x_s36_2 == lx1)) && (y_s40_2 == ly1_0)) && (x2_s44_0 == lx2)) && (y2_s48_0 == ly2_0)) && (0 == dashed)) && (1 == arrow));
              _pac_sc_s18 = _pac_sc_s18_s20;
            }
            _pac_sc_s15_s17 = _pac_sc_s18;
          }
          dummyEndReflection();
          newCost_0 = reflection_cost + 1;
          _pac_sc_s15 = _pac_sc_s15_s17;
        }
        loop_body_cost = 1 + newCost_0;
        _pac_sc_s28 = _pac_sc_s15;
      }
      _pac_sc_s12_s14 = _pac_sc_s28;
    }
    assert (loop_body_cost != 0); //Assert at tmpn1L3R8.sk:104 (-1233584306076905409)
    newCost = loop_body_cost + 1;
    _pac_sc_s12 = _pac_sc_s12_s14;
  }
  dummyEndLoop();
  _out = _pac_sc_s12;
  minimize((1 + newCost) + 1)
''')
#    e = [circle(4,10)] + [ _i for i in range(0,3) for _i in ([line(3*i + 1,4,3*i + 1,2,arrow = True,solid = True)] + reflect(y = 6)([circle(3*i + 1,1)] + [line(4,9,3*i + 1,6,arrow = True,solid = True)])) ]
    print e
    for h in e.hoistReflection():
        print h
        showImage(fastRender(h.convertToSequence()))
#    print len(e)
    # print e
    # for p in e.extrapolations():
    #     showImage(fastRender(p.convertToSequence()))
