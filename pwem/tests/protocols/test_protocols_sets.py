#!/usr/bin/env python

# ***************************************************************************
# * Authors:     Roberto Marabini (roberto@cnb.csic.es)
# *              Jordi Burguet Castell (jburguet@cnb.csic.es)
# *
# * Unidad de Bioinformatica of Centro Nacional de Biotecnologia, CSIC
# *
# * This program is free software; you can redistribute it and/or modify
# * it under the terms of the GNU General Public License as published by
# * the Free Software Foundation; either version 3 of the License, or
# * (at your option) any later version.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# * GNU General Public License for more details.
# *
# * You should have received a copy of the GNU General Public License
# * along with this program; if not, write to the Free Software
# * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
# * 02111-1307  USA
# *
# *  All comments concerning this program package may be sent to the
# *  e-mail address 'scipion@cnb.csic.es'
# *
# **************************************************************************


import logging
logger = logging.getLogger(__name__)
import random
import unittest

from pwem.protocols import ProtUserSubSet
from pyworkflow.tests import DataSet

try:
    from itertools import izip
except ImportError:
    izip = zip

import pyworkflow.tests as pwtests
import pyworkflow.utils as pwutils

import pwem.protocols as emprot
import pwem.objects as emobj

# Used by Roberto's test, where he creates the particles "by hand"
from pwem.objects.data import Particle, SetOfParticles, Acquisition, CTFModel
from pyworkflow.utils.utils import prettyDict
from pyworkflow.object import Float


class TestSets(pwtests.BaseTest):
    """Run different tests related to the set operations."""

    @classmethod
    def setUpClass(cls):
        """Prepare the data that we will use later on."""

        logger.info(pwutils.greenStr(" Set Up - Collect data ".center(75, '-')))

        pwtests.setupTestProject(cls)  # defined in BaseTest, creates cls.proj

        cls.dataset_xmipp = pwtests.DataSet.getDataSet('xmipp_tutorial')
        cls.dataset_mda = pwtests.DataSet.getDataSet('mda')
        cls.dataset_ribo = pwtests.DataSet.getDataSet('ribo_movies')
        cls.datasetRelion = pwtests.DataSet.getDataSet('relion_tutorial')

        #
        # Imports
        #
        new = cls.proj.newProtocol  # short notation
        launch = cls.proj.launchProtocol
        # Micrographs
        # NOTE: This dataset has 3 mic with heterogeneous dimensions!! But so
        # far is not failing, should it?
        logger.info(pwutils.magentaStr("==> Importing data - micrographs"))
        p_imp_micros = new(emprot.ProtImportMicrographs,
                           filesPath=cls.dataset_xmipp.getFile('allMics'),
                           samplingRate=1.237, voltage=300)
        launch(p_imp_micros, wait=True)
        cls.micros = p_imp_micros.outputMicrographs

        # Micrographs SMALL - This is a mic with different dimensions
        logger.info(pwutils.magentaStr("==> Importing data - micrographs SMALL"))
        p_imp_micros = new(emprot.ProtImportMicrographs,
                           filesPath=cls.dataset_xmipp.getFile('mic3'),
                           samplingRate=1.237, voltage=300)
        launch(p_imp_micros, wait=True)
        cls.microsSmall = p_imp_micros.outputMicrographs

        # Volumes
        logger.info(pwutils.magentaStr("==> Importing data - volumes"))
        p_imp_volumes = new(emprot.ProtImportVolumes,
                            filesPath=cls.dataset_xmipp.getFile('volumes'),
                            samplingRate=9.896)
        launch(p_imp_volumes, wait=True)
        cls.vols = p_imp_volumes.outputVolumes

        # Movies
        logger.info(pwutils.magentaStr("==> Importing data - movies"))
        p_imp_movies = new(emprot.ProtImportMovies,
                           filesPath=cls.dataset_ribo.getFile('movies'),
                           samplingRate=2.37, magnification=59000,
                           voltage=300, sphericalAberration=2.0,
                           gainFile=cls.dataset_ribo.getFile('volume'),
                           darkFile=cls.dataset_ribo.getFile('volume'))
        launch(p_imp_movies, wait=True)
        cls.movies = p_imp_movies.outputMovies

        # Particles
        logger.info(pwutils.magentaStr("==> Importing data - particles"))
        p_imp_particles = new(emprot.ProtImportParticles,
                              filesPath=cls.dataset_mda.getFile('particles'),
                              samplingRate=3.5)
        launch(p_imp_particles, wait=True)
        cls.particles = p_imp_particles.outputParticles

        # Particles with micId
        logger.info(pwutils.magentaStr("==> Importing data - particles with micId"))
        relionFile = 'import/case2/relion_it015_data.star'
        pImpPartMicId = new(emprot.ProtImportParticles,
                            objLabel='from relion (auto-refine 3d)',
                            importFrom=emprot.ProtImportParticles.IMPORT_FROM_RELION,
                            starFile=cls.datasetRelion.getFile(relionFile),
                            magnification=10000,
                            samplingRate=7.08,
                            haveDataBeenPhaseFlipped=True)
        launch(pImpPartMicId, wait=True)
        cls.partMicId = pImpPartMicId.outputParticles
        cls.micsMicId = pImpPartMicId.outputMicrographs

        # Coordinates  -  Oh, I don't know of any example of coord. import :(

    #
    # Helper functions
    #
    def split(self, em_set, n, randomize):
        """Return a run split protocol over input set em_set."""

        p_split = self.proj.newProtocol(emprot.ProtSplitSet, numberOfSets=n)
        p_split.inputSet.set(em_set)
        p_split.randomize.set(randomize)
        self.proj.launchProtocol(p_split, wait=True)
        return p_split

    @staticmethod
    def outputs(p):
        """Iterator over all the elements in the outputs of protocol p."""
        for key, output in p.iterOutputAttributes():
            yield output

    #
    # The tests themselves.
    #
    def testSplit(self):
        """Test that the split operation works as expected."""

        logger.info(pwutils.greenStr(" Test Split ".center(75, '-')))

        def check(set0, n=2, randomize=False):
            # Simple checks on split sets from set0.
            logger.info(pwutils.magentaStr("==> Check split of %s" % type(set0).__name__))
            unsplit_set = [x.strId() for x in set0]
            p_split = self.split(set0, n=n, randomize=randomize)
            # Are all output elements of the protocol in the original set?
            for em_set in self.outputs(p_split):
                for elem in em_set:
                    self.assertTrue(elem.strId() in unsplit_set)
            # Number of elements of all split sets equal to original number?
            self.assertEqual(sum(len(x) for x in self.outputs(p_split)),
                             len(set0))

        check(self.micros)
        check(self.micros, randomize=True)
        check(self.vols)
        check(self.movies)
        check(self.particles)
        check(self.particles, n=4)

    def testSubsetByParams(self):
        """Test that the subset operation using parameters works as expected."""

        logger.info(pwutils.greenStr(" Test Subset by params".center(75, '-')))

        # Launch random subset
        p_subset = self.newProtocol(emprot.ProtSubSet)
        p_subset.setObjLabel('Random subset')
        p_subset.inputFullSet.set(self.particles)
        p_subset.chooseAtRandom.set(True)
        p_subset.nElements.set(10)
        self.launchProtocol(p_subset)

        self.assertSetSize(p_subset.outputParticles, 10)

        # Launch subset by ids
        p_subset = self.newProtocol(emprot.ProtSubSet)
        p_subset.setObjLabel('Subset by ids')
        p_subset.inputFullSet.set(self.particles)
        p_subset.selectIds.set(True)
        p_subset.range.set("1-4, 8, 1000") # Last one 1000 should be skipped as is missing in the set.
        self.launchProtocol(p_subset)

        self.assertSetSize(p_subset.outputParticles, 5)
        self.assertIsNotNone(p_subset.outputParticles[8], "Subset by id did not picked item 8.")

    def testSubsetByRange(self):
        logger.info(pwutils.greenStr(" Test Subset by Range"))

        particles = [p.clone() for p in self.particles]

        def _equal(part1, part2):
            return part1.getObjDict() == part2.getObjDict()

        # Launch random subset
        ps1 = self.newProtocol(emprot.ProtSubSet)
        ps1.inputFullSet.set(self.particles)
        ps1.setObjLabel('Range 1')
        ps1.selectIds.set(True)
        ps1.range.set('1-10')
        self.launchProtocol(ps1)
        self.assertSetSize(ps1.outputParticles, 10)
        self.assertTrue(_equal(particles[0], ps1.outputParticles.getFirstItem()))

        ps2 = self.newProtocol(emprot.ProtSubSet)
        ps2.inputFullSet.set(self.particles)
        ps2.setObjLabel('Range 2')
        ps2.selectIds.set(True)
        ps2.range.set('11-20')
        self.launchProtocol(ps2)
        self.assertSetSize(ps2.outputParticles, 10)
        self.assertTrue(_equal(particles[10], ps2.outputParticles.getFirstItem()))

    def testSubsetIntersection(self):
        """Test that the subset operation works as expected."""

        logger.info(pwutils.greenStr(" Test Subset ".center(75, '-')))

        def check(set0, n1=2, n2=2):
            """Simple checks on subsets, coming from split sets of set0."""
            logger.info(pwutils.magentaStr("==> Check subset of %s" % type(set0).__name__))
            p_split1 = self.split(set0, n=n1, randomize=True)
            p_split2 = self.split(set0, n=n2, randomize=True)

            setFull = random.choice(list(self.outputs(p_split1)))
            setSub = random.choice(list(self.outputs(p_split2)))

            label = '%s - %s,%s ' % (set0.getClassName(), n1, n2)
            # Launch intersection subset
            p_subset = self.newProtocol(emprot.ProtSubSet)
            p_subset.setObjLabel(label + 'intersection')
            p_subset.inputFullSet.set(setFull)
            p_subset.inputSubSet.set(setSub)
            self.launchProtocol(p_subset)

            # Launch difference subset
            p_subset_diff = self.proj.copyProtocol(p_subset)
            p_subset_diff.setOperation.set(p_subset_diff.SET_DIFFERENCE)
            p_subset_diff.setObjLabel(label + 'difference')
            self.launchProtocol(p_subset_diff)

            setFullIds = setFull.getIdSet()
            setSubIds = setSub.getIdSet()
            n = len(setFull)

            # Check intersection
            outputs = [o for o in self.outputs(p_subset)]
            n1 = 0
            if outputs:
                output = outputs[0]

                # Check properties
                self.assertTrue(set0.equalAttributes(output,
                                                     ignore=['_mapperPath', '_size'],
                                                     verbose=True),
                                "Intersection subset attributes are wrong")

                n1 = len(output)
                for elem in output:
                    self.assertTrue(elem.getObjId() in setFullIds)
                    self.assertTrue(elem.getObjId() in setSubIds,
                                    'object id %s not in set: %s'
                                    % (elem.getObjId(), setSubIds))

            # Check difference
            outputs = [o for o in self.outputs(p_subset_diff)]
            n2 = 0
            if outputs:
                output_diff = outputs[0]
                # Check properties
                self.assertTrue(set0.equalAttributes(output_diff,
                                                     ignore=['_mapperPath', '_size'],
                                                     verbose=True),
                                "In subset attributes are wrong")

                n2 = len(output_diff)
                for elem in output_diff:
                    self.assertTrue(elem.getObjId() in setFullIds)
                    self.assertTrue(elem.getObjId() not in setSubIds)

            self.assertTrue(n >= n1)
            self.assertTrue(n >= n2)
            self.assertEqual(n, n1 + n2)

        check(self.movies)
        check(self.particles)
        check(self.particles, n1=3, n2=5)

    def testSubsetByMic(self):
        """Test that the subset by Mic operation works as expected."""
        logger.info( pwutils.greenStr(" Test Subset by Mic".center(75, '-')))
        "Simple checks on subsets, coming from split sets of setMics."
        logger.info(pwutils.magentaStr("==> Check subset of %s by %s"
                                 % (type(self.partMicId).__name__,
                                    type(self.micsMicId).__name__)))

        # launch the protocol for a certain mics input
        def launchSubsetByMic(micsSubset):
            pSubsetbyMic = self.newProtocol(emprot.ProtSubSetByMic)
            pSubsetbyMic.inputParticles.set(self.partMicId)
            pSubsetbyMic.inputMicrographs.set(micsSubset)
            self.launchProtocol(pSubsetbyMic)
            return pSubsetbyMic.outputParticles

        # Check if the Output is generated, the subset size is correct and
        #  the micId of the particle with certain partId is correct.
        def checkAsserts(setParts, size, partId, micId):
            self.assertIsNotNone(setParts, "Output SetOfParticles"
                                           " were not created.")
            self.assertEqual(setParts.getSize(), size,
                             "The number of created particles is incorrect.")
            p = setParts[partId]
            self.assertEqual(p.getMicId(), micId)

        # Whole set of micrographs
        setMics = self.micsMicId
        # Create a subsets of Mics to apply the protocol
        pSplit = self.split(setMics, n=2, randomize=False)
        setMics2 = pSplit.outputMicrographs02
        # Create a subset of a single micrograph to apply the protocol
        pSplit = self.split(setMics, n=20, randomize=False)
        setMics3 = pSplit.outputMicrographs03

        # Launch subset by mics protocol with the whole set of Mics
        partByMic1 = launchSubsetByMic(setMics)
        # Launch subset by mics protocol with a subset of Mics
        partByMic2 = launchSubsetByMic(setMics2)
        # Launch subset by mics protocol with a single SetOfMics
        partByMic3 = launchSubsetByMic(setMics3)

        # Assertions for the three sets
        checkAsserts(partByMic1, self.partMicId.getSize(), 1885, 7)
        checkAsserts(partByMic2, 2638, 4330, 16)
        checkAsserts(partByMic3, 270, 725, 3)

    def testSubsetByCoord(self):
        """Test that the subset by Coord operation works as expected."""
        logger.info(pwutils.greenStr(" Test Subset by Coord".center(75, '-')))

        p_extract_coordinates = self.newProtocol(emprot.ProtExtractCoords)
        p_extract_coordinates.inputParticles.set(self.partMicId)
        p_extract_coordinates.inputMicrographs.set(self.micsMicId)
        self.launchProtocol(p_extract_coordinates)

        p_subset_by_coords = self.newProtocol(emprot.ProtSubSetByCoord)
        p_subset_by_coords.inputParticles.set(self.partMicId)
        p_subset_by_coords.inputCoordinates.set(p_extract_coordinates.outputCoordinates)
        self.launchProtocol(p_subset_by_coords)
        self.assertIsNotNone(p_subset_by_coords.outputParticles, "Output SetOfParticles were not created.")
        self.assertEqual(p_subset_by_coords.outputParticles.getSize(), 5236,
                         "The number of created particles is incorrect.")

    def testMerge(self):
        """Test that the union operation works as expected."""

        logger.info(pwutils.greenStr(" Test Merge ".center(75, '-')))

        def check(set0):
            # Simple checks on merge, coming from many split sets of set0.
            logger.info(pwutils.magentaStr("==> Check merge of %s" % type(set0).__name__))
            p_union = self.proj.newProtocol(emprot.ProtUnionSet)

            setsIds = []
            for i in range(random.randint(1, 5)):
                n = random.randint(1, len(set0) // 2)
                p_split = self.split(set0, n=n, randomize=True)
                setRandom = random.choice(list(self.outputs(p_split)))
                setsIds.append([x.strId() for x in setRandom])
                p_union.inputSets.append(setRandom)
            self.proj.launchProtocol(p_union, wait=True)

            output = next(self.outputs(p_union))  # first (and only!) output
            self.assertEqual(len(output), sum(len(x) for x in setsIds))
            # We might be able to do more interesting tests, using the
            # collected setsIds.

        check(self.micros)
        check(self.vols)
        check(self.movies)
        check(self.particles)

    def testMergeAlternateColumn(self):
        """Test that the union operation works as expected.
        Even if the order of the columns do not match.
        That is, M1(a,b,c) U M2(a,c,b)"""
        # Create two sets of particles
        inFileNameMetadata1 = self.proj.getTmpPath('particles1.sqlite')
        inFileNameMetadata2 = self.proj.getTmpPath('particles2.sqlite')
        imgSet1 = SetOfParticles(filename=inFileNameMetadata1)
        imgSet2 = SetOfParticles(filename=inFileNameMetadata2)

        inFileNameData = self.proj.getTmpPath('particles.stk')
        img1 = Particle()
        img2 = Particle()
        attrb1 = [11, 12, 13, 14]
        attrb2 = [21, 22, 23, 24]
        counter = 0

        for i in range(1, 3):
            img1.cleanObjId()
            img1.setLocation(i, inFileNameData)
            img1.setMicId(i % 3)
            img1.setClassId(i % 5)
            img1.setSamplingRate(1.)
            img1._attrb1 = Float(attrb1[counter])
            img1._attrb2 = Float(attrb2[counter])
            imgSet1.append(img1)
            counter += 1

        for i in range(1, 3):
            img2.cleanObjId()
            img2.setLocation(i, inFileNameData)
            img2.setClassId(i % 5)
            img2.setMicId(i % 3)
            img2.setSamplingRate(2.)
            img2._attrb1 = Float(attrb1[counter])
            img2._attrb2 = Float(attrb2[counter])
            imgSet2.append(img2)
            counter += 1

        imgSet1.write()
        imgSet2.write()

        # import them
        protImport1 = self.newProtocol(emprot.ProtImportParticles,
                                       objLabel='import set1',
                                       importFrom=emprot.ProtImportParticles.IMPORT_FROM_SCIPION,
                                       sqliteFile=inFileNameMetadata1,
                                       magnification=10000,
                                       samplingRate=7.08,
                                       haveDataBeenPhaseFlipped=True)
        self.launchProtocol(protImport1)

        protImport2 = self.newProtocol(emprot.ProtImportParticles,
                                       objLabel='import set2',
                                       importFrom=emprot.ProtImportParticles.IMPORT_FROM_SCIPION,
                                       sqliteFile=inFileNameMetadata2,
                                       magnification=10000,
                                       samplingRate=7.08,
                                       haveDataBeenPhaseFlipped=True)
        self.launchProtocol(protImport2)

        # create merge protocol
        p_union = self.newProtocol(emprot.ProtUnionSet,
                                   objLabel='join diff column order',
                                   ignoreExtraAttributes=True)
        p_union.inputSets.append(protImport1.outputParticles)
        p_union.inputSets.append(protImport2.outputParticles)
        self.proj.launchProtocol(p_union, wait=True)
        # assert
        counter = 0
        for img in p_union.outputSet:
            self.assertAlmostEqual(attrb1[counter], img._attrb1, 4)
            self.assertAlmostEqual(attrb2[counter], img._attrb2, 4)
            counter += 1

    def testMergeDifferentAttrs(self):
        """ Test merge from subsets with different attributes.
        That is, M1(a,b,c) U M2(a,b,c,d)"""

        # create two set of particles
        inFileNameMetadata1 = self.proj.getTmpPath('particles11.sqlite')
        inFileNameMetadata2 = self.proj.getTmpPath('particles22.sqlite')
        imgSet1 = SetOfParticles(filename=inFileNameMetadata1)
        imgSet2 = SetOfParticles(filename=inFileNameMetadata2)

        inFileNameData = self.proj.getTmpPath('particles.stk')
        # Start ids 4
        img1 = Particle(objId=4)
        img2 = Particle(objId=4)
        attrb1 = [11, 12, 13, 14]
        attrb2 = [21, 22, 23, 24]
        attrb3 = [31, 32]
        counter = 0
        # Test the join handles different attributes at a second level
        ctf1 = CTFModel(defocusU=1000, defocusV=1000, defocusAngle=0)
        ctf2 = CTFModel(defocusU=2000, defocusV=2000, defocusAngle=0)
        ctf2._myOwnQuality = Float(1.)
        img1.setCTF(ctf1)
        img2.setCTF(ctf2)

        for i in range(1, 3):
            # Increment Id
            img1.setObjId(img1.getObjId() + 1)
            img1.setLocation(i, inFileNameData)
            img1.setMicId(i % 3)
            img1.setClassId(i % 5)
            img1.setSamplingRate(1.)
            img1._attrb1 = Float(attrb1[counter])
            img1._attrb2 = Float(attrb2[counter])
            img1._attrb3 = Float(attrb3[counter])
            imgSet1.append(img1)
            counter += 1

        for i in range(1, 3):
            # Increment Id
            img2.setObjId(img2.getObjId() + 1)
            img2.setLocation(i, inFileNameData)
            img2.setClassId(i % 5)
            img2.setMicId(i % 3)
            img2.setSamplingRate(2.)
            img2._attrb1 = Float(attrb1[counter])
            img2._attrb2 = Float(attrb2[counter])
            imgSet2.append(img2)
            counter += 1

        imgSet1.write()
        imgSet2.write()

        # import them
        protImport1 = self.newProtocol(emprot.ProtImportParticles,
                                       objLabel='import set1',
                                       importFrom=emprot.ProtImportParticles.IMPORT_FROM_SCIPION,
                                       sqliteFile=inFileNameMetadata1,
                                       magnification=10000,
                                       samplingRate=7.08,
                                       haveDataBeenPhaseFlipped=True
                                       )
        self.launchProtocol(protImport1)

        protImport2 = self.newProtocol(emprot.ProtImportParticles,
                                       objLabel='import set2',
                                       importFrom=emprot.ProtImportParticles.IMPORT_FROM_SCIPION,
                                       sqliteFile=inFileNameMetadata2,
                                       magnification=10000,
                                       samplingRate=7.08,
                                       haveDataBeenPhaseFlipped=True
                                       )
        self.launchProtocol(protImport2)

        # create merge protocol
        p_union = self.newProtocol(emprot.ProtUnionSet,
                                   objLabel='join different attrs',
                                   ignoreExtraAttributes=True)
        p_union.inputSets.append(protImport1.outputParticles)
        p_union.inputSets.append(protImport2.outputParticles)
        self.proj.launchProtocol(p_union, wait=True)

        counter = 0

        for img in p_union.outputSet:
            self.assertAlmostEqual(attrb1[counter], img._attrb1, 4)
            self.assertAlmostEqual(attrb2[counter], img._attrb2, 4)
            self.assertFalse(hasattr(img, '_attrb3'),
                             "join should not have attrb3")
            self.assertTrue(hasattr(img, '_attrb2'),
                            "join should have attrb2")
            ctf = img.getCTF()
            self.assertIsNotNone(ctf, "Image should have CTF after join")
            self.assertFalse(hasattr(ctf, '_myOwnQuality'),
                             "CTF should not have non common attributes")

            # Assert ids
            self.assertEqual(counter + 5, img.getObjId(),
                             "Object id's not kept.")
            counter += 1

    def testOrderBy(self):
        """ create set of particles and orderby a given attribute
        """
        # This function was written by Roberto. It does things
        # differently, so let's keep it for reference.

        # create set of particles

        inFileNameMetadata = self.proj.getTmpPath('particlesOrderBy.sqlite')
        inFileNameData = self.proj.getTmpPath('particlesOrderBy.stk')

        imgSet = SetOfParticles(filename=inFileNameMetadata)
        imgSet.setSamplingRate(1.5)
        acq = Acquisition()
        acq.setAmplitudeContrast(0.1)
        acq.setMagnification(10000)
        acq.setVoltage(200)
        acq.setSphericalAberration(2.0)

        imgSet.setAcquisition(acq)
        img = Particle()

        for i in range(1, 10):
            img.setLocation(i, inFileNameData)
            img.setMicId(i % 3)
            img.setClassId(i % 5)
            imgSet.append(img)
            img.cleanObjId()

        imgSet.write()
        # now import the dataset
        prot1 = self.newProtocol(emprot.ProtImportParticles,
                                 importFrom=emprot.ProtImportParticles.IMPORT_FROM_SCIPION,
                                 sqliteFile=inFileNameMetadata,
                                 magnification=10000,
                                 samplingRate=1.5
                                 )
        prot1.setObjLabel('from sqlite (test-sets)')
        self.launchProtocol(prot1)

        if prot1.outputParticles is None:
            raise Exception(
                'Import of images: %s, failed. outputParticles is None.'
                % inFileNameMetadata)

        protSplitSet = self.newProtocol(emprot.ProtSplitSet,
                                        inputSet=prot1.outputParticles,
                                        numberOfSets=2,
                                        randomize=True)
        self.launchProtocol(protSplitSet)

        inputSets = [protSplitSet.outputParticles01,
                     protSplitSet.outputParticles02]
        outputSet = SetOfParticles(filename=self.proj.getTmpPath('gold.sqlite'))
        for itemSet in inputSets:
            for obj in itemSet:
                outputSet.append(obj)

        for item1, item2 in izip(imgSet, outputSet):
            if not item1.equalAttributes(item2):
                logger.info("Items differ:")
                prettyDict(item1.getObjDict())
                prettyDict(item2.getObjDict())
            self.assertTrue(item1.equalAttributes(item2), )

    def testEmptiness(self):

        self.assertSetSize(self.particles)
        self.assertSetSize(self.particles, 76)

    def testJoinValidation(self):

        # Create a merge protocol
        p_union = self.newProtocol(emprot.ProtUnionSet,
                                   objLabel='invalid join',
                                   ignoreExtraAttributes=True)
        p_union.inputSets.append(self.microsSmall)
        p_union.inputSets.append(self.micros)

        with self.assertRaises(Exception):
            self.launchProtocol(p_union)


class TestUserSubSet(pwtests.BaseTest):
    @classmethod
    def setUpClass(cls):
        cls.dataset = DataSet.getDataSet('model')
        cls.selectionFn = cls.dataset.getFile('classesSelection')
        pwtests.setupTestProject(cls)

    def test_2DClasses(self):
        """ Load an existing SetOfClasses and test basic properties
        such us: _mapperPath, iteration and others.
        """
        emProt = self.newProtocol(emprot.ProtImportParticles)
        classes2DSet = emobj.SetOfClasses2D(filename=self.selectionFn)
        emProt._defineOutputs(outputClasses=classes2DSet)
        emProt.setFinished()
        emProt._store()

        batchProt = self.newProtocol(ProtUserSubSet,
                                     inputObject=classes2DSet,
                                     sqliteFile=self.selectionFn + ',',
                                     outputClassName='SetOfClasses2D')
        self.launchProtocol(batchProt)


if __name__ == '__main__':
    unittest.main()
